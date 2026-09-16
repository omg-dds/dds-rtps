use clap::{Parser, ValueEnum};
use dust_dds::{
    configuration::DustDdsConfigurationBuilder,
    dds_async::{topic::TopicAsync, topic_description::TopicDescriptionAsync},
    domain::{
        domain_participant::DomainParticipant,
        domain_participant_factory::DomainParticipantFactory,
        domain_participant_listener::DomainParticipantListener,
    },
    infrastructure::{
        error::DdsError,
        instance::InstanceHandle,
        listener::NO_LISTENER,
        qos::{DataReaderQos, DataWriterQos, PublisherQos, QosKind, SubscriberQos},
        qos_policy::{
            self, DataRepresentationQosPolicy, DurabilityQosPolicy, HistoryQosPolicy,
            HistoryQosPolicyKind, OwnershipQosPolicy, OwnershipQosPolicyKind,
            OwnershipStrengthQosPolicy, PartitionQosPolicy, ReliabilityQosPolicy,
            XCDR_DATA_REPRESENTATION, XCDR2_DATA_REPRESENTATION,
        },
        sample_info::{ANY_INSTANCE_STATE, ANY_SAMPLE_STATE, ANY_VIEW_STATE, InstanceStateKind},
        status::{InconsistentTopicStatus, NO_STATUS, StatusKind},
        time::{Duration, DurationKind},
    },
    publication::data_writer::DataWriter,
    subscription::data_reader::DataReader,
};
use rand::{Rng, random, thread_rng};
use std::{
    collections::HashMap,
    fmt::{Debug, Display},
    io::Write,
    process::{ExitCode, Termination},
    sync::mpsc::Receiver,
};

include!(concat!(env!("OUT_DIR"), "/idl/shape.rs"));

fn qos_policy_name(id: i32) -> String {
    match id {
        qos_policy::DATA_REPRESENTATION_QOS_POLICY_ID => "DATAREPRESENTATION",
        qos_policy::DEADLINE_QOS_POLICY_ID => "DEADLINE",
        qos_policy::DESTINATIONORDER_QOS_POLICY_ID => "DESTINATIONORDER",
        qos_policy::DURABILITY_QOS_POLICY_ID => "DURABILITY",
        qos_policy::DURABILITYSERVICE_QOS_POLICY_ID => "DURABILITYSERVICE",
        qos_policy::ENTITYFACTORY_QOS_POLICY_ID => "ENTITYFACTORY",
        qos_policy::GROUPDATA_QOS_POLICY_ID => "GROUPDATA",
        qos_policy::HISTORY_QOS_POLICY_ID => "HISTORY",
        qos_policy::LATENCYBUDGET_QOS_POLICY_ID => "LATENCYBUDGET",
        qos_policy::LIFESPAN_QOS_POLICY_ID => "LIFESPAN",
        qos_policy::LIVELINESS_QOS_POLICY_ID => "LIVELINESS",
        qos_policy::OWNERSHIP_QOS_POLICY_ID => "OWNERSHIP",
        qos_policy::PARTITION_QOS_POLICY_ID => "PARTITION",
        qos_policy::PRESENTATION_QOS_POLICY_ID => "PRESENTATION",
        qos_policy::READERDATALIFECYCLE_QOS_POLICY_ID => "READERDATALIFECYCLE",
        qos_policy::RELIABILITY_QOS_POLICY_ID => "RELIABILITY",
        qos_policy::RESOURCELIMITS_QOS_POLICY_ID => "RESOURCELIMITS",
        qos_policy::TIMEBASEDFILTER_QOS_POLICY_ID => "TIMEBASEDFILTER",
        qos_policy::TOPICDATA_QOS_POLICY_ID => "TOPICDATA",
        qos_policy::TRANSPORTPRIORITY_QOS_POLICY_ID => "TRANSPORTPRIORITY",
        qos_policy::USERDATA_QOS_POLICY_ID => "USERDATA",
        qos_policy::WRITERDATALIFECYCLE_QOS_POLICY_ID => "WRITERDATALIFECYCLE",
        _ => "UNKNOWN",
    }
    .to_string()
}

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum, Debug)]
#[clap(rename_all = "kebab_case")]
enum FinalInstanceState {
    /// unregister
    U,
    /// dispose
    D,
}

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum, Debug)]
#[clap(rename_all = "kebab_case")]
enum AccessScope {
    /// INSTANCE
    I,
    /// TOPIC
    T,
    /// GROUP
    G,
}

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, Debug)]
enum Verbosity {
    Error = 1,
    Debug = 2,
}

struct Logger {
    verbosity: Verbosity,
}

impl Logger {
    fn new(v: Verbosity) -> Self {
        Self { verbosity: v }
    }

    fn log_message(&self, message: impl AsRef<str>, level: Verbosity) {
        if (level as u8) <= (self.verbosity as u8) {
            println!("{}", message.as_ref());
        }
    }
}

#[derive(Parser, Clone, Debug)]
#[command(author, version, about, long_about = None)]
struct Options {
    /// publish samples
    #[clap(short = 'P', default_value_t = false)]
    publish: bool,

    /// subscribe samples
    #[clap(short = 'S', default_value_t = false)]
    subscribe: bool,

    /// domain id
    #[clap(short = 'd', default_value_t = 0)]
    domain_id: i32,

    /// BEST_EFFORT reliability
    #[clap(short = 'b', default_value_t = false)]
    best_effort_reliability: bool,

    /// RELIABLE reliability
    #[clap(short = 'r', default_value_t = false)]
    reliable_reliability: bool,

    /// keep history depth [0: KEEP_ALL]
    #[clap(short = 'k', default_value_t = -1, allow_negative_numbers = true)]
    history_depth: i32,

    /// set a 'deadline' with interval (ms) [0: OFF]
    #[clap(short = 'f', default_value_t = 0)]
    deadline_interval: u64,

    /// set ownership strength [-1: SHARED]
    #[clap(short = 's', default_value_t = -1, allow_negative_numbers = true)]
    ownership_strength: i32,

    /// set the topic name
    #[clap(short = 't')]
    topic_name: Option<String>,

    /// set color to publish (filter if subscriber)
    #[clap(short = 'c', default_value = None)]
    color: Option<String>,

    /// set a 'partition' string
    #[clap(short = 'p')]
    partition: Option<String>,

    /// set durability [v: VOLATILE,  l: TRANSIENT_LOCAL, t: TRANSIENT, p: PERSISTENT]
    #[clap(short = 'D', default_value_t = 'v')]
    durability_kind: char,

    /// set data representation [1: XCDR, 2: XCDR2]
    #[clap(short = 'x', default_value_t = 1)]
    data_representation: u16,

    /// print Publisher's samples
    #[clap(short = 'w', default_value_t = false)]
    print_writer_samples: bool,

    /// set shapesize (0: increase the size for every sample)
    #[clap(short = 'z', default_value_t = 20)]
    shapesize: i32,

    /// use 'read()' instead of 'take()'
    #[clap(short = 'R', default_value_t = false)]
    use_read: bool,

    /// waiting period between 'write()' operations in ms. Default: 33ms
    #[clap(short = 'W', long = "write-period", default_value_t = 33)]
    write_period_ms: u64,

    /// waiting period between 'read()' or 'take()' operations in ms. Default: 100ms
    #[clap(short = 'A', long = "read-period", default_value_t = 100)]
    read_period_ms: u64,

    /// set log message verbosity [e: ERROR, d: DEBUG]
    #[clap(short = 'v', default_value_t = 'e')]
    log_message_verbosity: char,

    /// apply 'time based filter' with interval in ms [0: OFF]
    #[clap(short = 'i', long = "time-filter")]
    time_filter: Option<u64>,

    /// indicates the lifespan of a sample in ms
    #[clap(short = 'l', long = "lifespan")]
    lifespan: Option<u64>,

    /// indicates the number of iterations of the main loop. After that, the application will exit. Default: infinite
    #[clap(short = 'n', long = "num-iterations", default_value_t = 0)]
    num_iterations: u32,

    /// indicates the number of instances a DataWriter writes
    #[clap(short = 'I', long = "num-instances", default_value_t = 1)]
    num_instances: u32,

    /// indicates the number of topics created (using the same type)
    #[clap(short = 'E', long = "num-topics", default_value_t = 1)]
    num_topics: u32,

    /// indicates the action performed after the DataWriter finishes its execution (before deleting it):
    #[clap(short = 'M', long = "final-instance-state")]
    final_instance_state: Option<FinalInstanceState>,

    /// sets Presentation.access_scope to INSTANCE, TOPIC or GROUP
    #[clap(short = 'C', long = "access-scope")]
    access_scope: Option<AccessScope>,

    /// sets Presentation.coherent_access = true
    #[clap(short = 'T', long = "coherent", default_value_t = false)]
    coherent: bool,

    /// sets Presentation.ordered_access = true
    #[clap(short = 'O', long = "ordered", default_value_t = false)]
    ordered: bool,

    /// amount of samples sent for each DataWriter and instance that are grouped in a coherent set
    #[clap(short = 'H', long = "coherent-sample-count")]
    coherent_sample_count: Option<u32>,

    /// indicates the amount of bytes added to the samples written (for example to use large data)
    #[clap(short = 'B', long = "additional-payload-size", default_value_t = 0)]
    additional_payload_size: usize,

    /// uses take()/read() instead of take_next_instance() read_next_instance()
    #[clap(short = 'K', long = "take-read", default_value_t = false)]
    take_read: bool,

    /// indicates the periodic participant announcement period in ms. Default 0 (off)
    #[clap(short = 'N', long = "periodic-announcement", default_value_t = 0)]
    periodic_announcement: u64,

    /// set the data fragment size (default: 0, means not set)
    #[clap(short = 'Z', long = "datafrag-size", default_value_t = 0)]
    datafrag_size: u32,

    /// ContentFilteredTopic filter expression (quotes required around the expression). Cannot be used with -c on subscriber applications
    #[clap(short = 'F', long = "cft")]
    cft_expression: Option<String>,

    /// If set, the modulo operation is applied to the shapesize. This will make that shapesize is in the range [1,N]. This only applies if shapesize is increased (-z 0)
    #[clap(short = 'Q', long = "size-modulo")]
    size_modulo: Option<i32>,
}

impl Options {
    fn verbosity(&self) -> Verbosity {
        match self.log_message_verbosity {
            'd' => Verbosity::Debug,
            _ => Verbosity::Error,
        }
    }

    fn validate(&mut self, logger: &Logger) -> Result<(), ParsingError> {
        if self.topic_name.is_none() {
            logger.log_message("please specify topic name [-t]", Verbosity::Error);
            return Err(ParsingError);
        }

        if !self.publish && !self.subscribe {
            logger.log_message(
                "please specify publish [-P] or subscribe [-S]",
                Verbosity::Error,
            );
            return Err(ParsingError);
        }

        if self.publish && self.subscribe {
            logger.log_message(
                "please specify only one of: publish [-P] or subscribe [-S]",
                Verbosity::Error,
            );
            return Err(ParsingError);
        }

        if self.publish && self.color.is_none() {
            self.color = Some("BLUE".to_string());
            logger.log_message(
                "warning: color was not specified, defaulting to \"BLUE\"",
                Verbosity::Error,
            );
        }

        if self.publish && self.time_filter.unwrap_or(0) > 0 {
            logger.log_message(
                "warning: time base filter [--time-filter] ignored on publisher applications",
                Verbosity::Error,
            );
        }

        if self.publish && self.use_read {
            logger.log_message(
                "warning: use read [-R] ignored on publisher applications",
                Verbosity::Error,
            );
        }

        if self.publish && self.take_read {
            logger.log_message(
                "warning: --take-read ignored on publisher applications",
                Verbosity::Error,
            );
        }

        if self.publish && self.cft_expression.is_some() {
            logger.log_message(
                "warning: --cft ignored on publisher applications",
                Verbosity::Error,
            );
        }

        if self.subscribe && self.shapesize != 20 {
            logger.log_message(
                "warning: shapesize [-z] ignored on subscriber applications",
                Verbosity::Error,
            );
        }

        if self.subscribe && self.lifespan.unwrap_or(0) > 0 {
            logger.log_message(
                "warning: --lifespan ignored on subscriber applications",
                Verbosity::Error,
            );
        }

        if self.subscribe && self.num_instances > 1 {
            logger.log_message(
                "warning: --num-instances ignored on subscriber applications",
                Verbosity::Error,
            );
        }

        if self.subscribe && self.final_instance_state.is_some() {
            logger.log_message(
                "warning: --final-instance-state ignored on subscriber applications",
                Verbosity::Error,
            );
        }

        if self.subscribe && self.coherent_sample_count.unwrap_or(0) > 0 {
            logger.log_message(
                "warning: --coherent-sample-count ignored on subscriber applications",
                Verbosity::Error,
            );
        }

        if !self.coherent && !self.ordered && self.coherent_sample_count.unwrap_or(0) > 0 {
            logger.log_message(
                "warning: --coherent-sample-count ignored because not coherent, or ordered access enabled",
                Verbosity::Error,
            );
        }

        if self.subscribe && self.additional_payload_size > 0 {
            logger.log_message(
                "warning: --additional-payload-size ignored on subscriber applications",
                Verbosity::Error,
            );
        }

        if !self.coherent && !self.ordered && self.access_scope.is_some() {
            logger.log_message(
                "warning: --access-scope set but not coherent, or ordered access enabled",
                Verbosity::Error,
            );
        }

        if self.size_modulo.unwrap_or(0) > 0 && self.shapesize != 0 {
            logger.log_message(
                "warning: --size-modulo has no effect unless shapesize (-z) is set to 0",
                Verbosity::Error,
            );
        }

        if self.subscribe && self.color.is_some() && self.cft_expression.is_some() {
            logger.log_message(
                "error: cannot specify both --cft and -c for subscriber applications",
                Verbosity::Error,
            );
            return Err(ParsingError);
        }

        if self.datafrag_size > 65535 {
            logger.log_message(
                format!(
                    "incorrect value for datafrag-size, it must be <= 65535 bytes{}",
                    self.datafrag_size
                ),
                Verbosity::Error,
            );
            return Err(ParsingError);
        }

        Ok(())
    }

    fn print_debug_options(&self, logger: &Logger) {
        let app_kind = if self.publish {
            "publisher"
        } else {
            "subscriber"
        };
        let reliability_str = if self.best_effort_reliability {
            "BEST_EFFORT"
        } else {
            "RELIABLE"
        };
        let durability_str = match self.durability_kind {
            'l' => "TRANSIENT_LOCAL",
            't' => "TRANSIENT",
            'p' => "PERSISTENT",
            _ => "VOLATILE",
        };
        let data_rep_str = match self.data_representation {
            2 => "XCDR2",
            _ => "XCDR",
        };
        let reading_method = if self.use_read {
            if self.take_read {
                "read"
            } else {
                "read_next_instance"
            }
        } else {
            if self.take_read {
                "take"
            } else {
                "take_next_instance"
            }
        };
        let final_state_str = match self.final_instance_state {
            Some(FinalInstanceState::U) => "Unregister",
            Some(FinalInstanceState::D) => "Dispose",
            None => "not specified",
        };
        let access_scope_str = match self.access_scope {
            Some(AccessScope::I) => "INSTANCE_PRESENTATION_QOS",
            Some(AccessScope::T) => "TOPIC_PRESENTATION_QOS",
            Some(AccessScope::G) => "GROUP_PRESENTATION_QOS",
            None => "INSTANCE_PRESENTATION_QOS",
        };

        let mut msg = format!(
            "Shape Options: \n    Verbosity = {:?}\n    This application is a {}\n    DomainId = {}\n    ReliabilityKind = {}\n    DurabilityKind = {}\n    DataRepresentation = {}\n    HistoryDepth = {}\n    OwnershipStrength = {}\n    TimeBasedFilterInterval = {}ms\n    DeadlineInterval = {}ms\n    Shapesize = {}\n    Reading method = {}\n    Write period = {}ms\n    Read period = {}ms\n    Lifespan = {}ms\n    Number of iterations = {}\n    Number of instances = {}\n    Number of entities = {}\n    Coherent sets = {}\n    Ordered access = {}\n    Access Scope = {}\n    Coherent Sample Count = {}\n    Additional Payload Size = {}\n    Final Instance State = {}\n    Periodic Announcement Period = {}ms\n    Data Fragmentation Size = {} bytes",
            logger.verbosity,
            app_kind,
            self.domain_id,
            reliability_str,
            durability_str,
            data_rep_str,
            self.history_depth,
            self.ownership_strength,
            self.time_filter.unwrap_or(0),
            self.deadline_interval,
            self.shapesize,
            reading_method,
            self.write_period_ms,
            self.read_period_ms,
            self.lifespan.unwrap_or(0),
            self.num_iterations,
            self.num_instances,
            self.num_topics,
            if self.coherent { "true" } else { "false" },
            if self.ordered { "true" } else { "false" },
            access_scope_str,
            self.coherent_sample_count.unwrap_or(0),
            self.additional_payload_size,
            final_state_str,
            self.periodic_announcement,
            self.datafrag_size
        );

        if let Some(topic) = &self.topic_name {
            msg.push_str(&format!("\n    Topic = {}", topic));
        }
        if let Some(color) = &self.color {
            msg.push_str(&format!("\n    Color = {}", color));
        }
        if let Some(partition) = &self.partition {
            msg.push_str(&format!("\n    Partition = {}", partition));
        }

        logger.log_message(msg, Verbosity::Debug);
    }

    fn reliability_qos_policy(&self) -> ReliabilityQosPolicy {
        let mut reliability = DataWriterQos::default().reliability;
        if self.best_effort_reliability {
            reliability.kind = qos_policy::ReliabilityQosPolicyKind::BestEffort;
        }
        if self.reliable_reliability {
            reliability.kind = qos_policy::ReliabilityQosPolicyKind::Reliable;
        }
        reliability
    }

    fn partition_qos_policy(&self) -> PartitionQosPolicy {
        if let Some(partition) = &self.partition {
            PartitionQosPolicy {
                name: vec![partition.to_owned()],
            }
        } else {
            PartitionQosPolicy::default()
        }
    }

    fn durability_qos_policy(&self) -> DurabilityQosPolicy {
        DurabilityQosPolicy {
            kind: match self.durability_kind {
                'v' => qos_policy::DurabilityQosPolicyKind::Volatile,
                'l' => qos_policy::DurabilityQosPolicyKind::TransientLocal,
                't' => qos_policy::DurabilityQosPolicyKind::Transient,
                'p' => qos_policy::DurabilityQosPolicyKind::Persistent,
                _ => panic!("durability not valid"),
            },
        }
    }

    fn data_representation_qos_policy(&self) -> DataRepresentationQosPolicy {
        let data_representation = match self.data_representation {
            1 => XCDR_DATA_REPRESENTATION,
            2 => XCDR2_DATA_REPRESENTATION,
            _ => panic!("Wrong data representation"),
        };
        qos_policy::DataRepresentationQosPolicy {
            value: vec![data_representation],
        }
    }

    fn ownership_qos_policy(&self) -> OwnershipQosPolicy {
        OwnershipQosPolicy {
            kind: match self.ownership_strength {
                -1 => qos_policy::OwnershipQosPolicyKind::Shared,
                _ => qos_policy::OwnershipQosPolicyKind::Exclusive,
            },
        }
    }

    fn history_depth_qos_policy(&self) -> HistoryQosPolicy {
        match self.history_depth {
            -1 => HistoryQosPolicy::default(),
            0 => HistoryQosPolicy {
                kind: HistoryQosPolicyKind::KeepAll,
            },
            x if x >= 1 => HistoryQosPolicy {
                kind: HistoryQosPolicyKind::KeepLast(x as u32),
            },
            _ => panic!("history_depth not valid"),
        }
    }

    fn ownership_strength_qos_policy(&self) -> OwnershipStrengthQosPolicy {
        if self.ownership_strength < -1 {
            panic!("Ownership strength must be positive or zero")
        }
        OwnershipStrengthQosPolicy {
            value: self.ownership_strength,
        }
    }
}

impl Display for AccessScope {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            AccessScope::I => "INSTANCE_PRESENTATION_QOS",
            AccessScope::T => "TOPIC_PRESENTATION_QOS",
            AccessScope::G => "GROUP_PRESENTATION_QOS",
        })
    }
}

struct Listener;
impl DomainParticipantListener for Listener {
    async fn on_inconsistent_topic(
        &mut self,
        the_topic: TopicAsync,
        _status: InconsistentTopicStatus,
    ) {
        println!(
            "on_inconsistent_topic() topic: '{}'  type: '{}'",
            the_topic.get_name(),
            the_topic.get_type_name(),
        );
    }

    async fn on_offered_incompatible_qos(
        &mut self,
        the_writer: dust_dds::dds_async::data_writer::DataWriterAsync<()>,
        status: dust_dds::infrastructure::status::OfferedIncompatibleQosStatus,
    ) {
        let policy_name = qos_policy_name(status.last_policy_id);
        println!(
            "on_offered_incompatible_qos() topic: '{}'  type: '{}' : {:?} ({})",
            the_writer.get_topic().get_name(),
            the_writer.get_topic().get_type_name(),
            status.last_policy_id,
            policy_name
        );
    }

    async fn on_publication_matched(
        &mut self,
        the_writer: dust_dds::dds_async::data_writer::DataWriterAsync<()>,
        status: dust_dds::infrastructure::status::PublicationMatchedStatus,
    ) {
        if !the_writer.get_topic().get_name().starts_with("DCPS") {
            println!(
                "on_publication_matched() topic: '{}'  type: '{}' : matched readers {} (change = {})",
                the_writer.get_topic().get_name(),
                the_writer.get_topic().get_type_name(),
                status.current_count,
                status.current_count_change
            );
        }
    }

    async fn on_offered_deadline_missed(
        &mut self,
        the_writer: dust_dds::dds_async::data_writer::DataWriterAsync<()>,
        status: dust_dds::infrastructure::status::OfferedDeadlineMissedStatus,
    ) {
        println!(
            "on_offered_deadline_missed() topic: '{}'  type: '{}' : (total = {}, change = {})",
            the_writer.get_topic().get_name(),
            the_writer.get_topic().get_type_name(),
            status.total_count,
            status.total_count_change
        );
    }

    async fn on_liveliness_lost(
        &mut self,
        the_writer: dust_dds::dds_async::data_writer::DataWriterAsync<()>,
        status: dust_dds::infrastructure::status::LivelinessLostStatus,
    ) {
        println!(
            "on_liveliness_lost() topic: '{}'  type: '{}' : (total = {}, change = {})",
            the_writer.get_topic().get_name(),
            the_writer.get_topic().get_type_name(),
            status.total_count,
            status.total_count_change
        );
    }

    async fn on_requested_incompatible_qos(
        &mut self,
        the_reader: dust_dds::dds_async::data_reader::DataReaderAsync<()>,
        status: dust_dds::infrastructure::status::RequestedIncompatibleQosStatus,
    ) {
        let policy_name = qos_policy_name(status.last_policy_id);
        println!(
            "on_requested_incompatible_qos() topic: '{}'  type: '{}' : {} ({})\n",
            the_reader.get_topicdescription().get_name(),
            the_reader.get_topicdescription().get_type_name(),
            status.last_policy_id,
            policy_name
        );
    }

    async fn on_subscription_matched(
        &mut self,
        the_reader: dust_dds::dds_async::data_reader::DataReaderAsync<()>,
        status: dust_dds::infrastructure::status::SubscriptionMatchedStatus,
    ) {
        if !the_reader
            .get_topicdescription()
            .get_name()
            .starts_with("DCPS")
        {
            println!(
                "on_subscription_matched() topic: '{}'  type: '{}' : matched writers {} (change = {})",
                the_reader.get_topicdescription().get_name(),
                the_reader.get_topicdescription().get_type_name(),
                status.current_count,
                status.current_count_change
            );
        }
    }

    async fn on_requested_deadline_missed(
        &mut self,
        the_reader: dust_dds::dds_async::data_reader::DataReaderAsync<()>,
        status: dust_dds::infrastructure::status::RequestedDeadlineMissedStatus,
    ) {
        println!(
            "on_requested_deadline_missed() topic: '{}'  type: '{}' : (total = {}, change = {})\n",
            the_reader.get_topicdescription().get_name(),
            the_reader.get_topicdescription().get_type_name(),
            status.total_count,
            status.total_count_change
        );
    }

    async fn on_liveliness_changed(
        &mut self,
        the_reader: dust_dds::dds_async::data_reader::DataReaderAsync<()>,
        status: dust_dds::infrastructure::status::LivelinessChangedStatus,
    ) {
        println!(
            "on_liveliness_changed() topic: '{}'  type: '{}' : (alive = {}, not_alive = {})",
            the_reader.get_topicdescription().get_name(),
            the_reader.get_topicdescription().get_type_name(),
            status.alive_count,
            status.not_alive_count,
        );
    }
}

fn move_shape(
    shape: &mut ShapeType,
    x_vel: &mut i32,
    y_vel: &mut i32,
    da_width: i32,
    da_height: i32,
) {
    shape.x += *x_vel;
    shape.y += *y_vel;
    if shape.x < 0 {
        shape.x = 0;
        *x_vel = -*x_vel;
    }
    if shape.x > da_width {
        shape.x = da_width;
        *x_vel = -*x_vel;
    }
    if shape.y < 0 {
        shape.y = 0;
        *y_vel = -*y_vel;
    }
    if shape.y > da_height {
        shape.y = da_height;
        *y_vel = -*y_vel;
    }
}

fn init_publisher(
    participant: &DomainParticipant,
    options: &Options,
    logger: &Logger,
) -> Result<Vec<DataWriter<ShapeType>>, InitializeError> {
    logger.log_message("Running init_publisher() function", Verbosity::Debug);

    if options.coherent {
        logger.log_message(
            "    Presentation Coherent Access = not supported",
            Verbosity::Error,
        );
        return Err(InitializeError(
            "Presentation Coherent Access = not supported".to_string(),
        ));
    }
    if options.ordered {
        logger.log_message(
            "    Presentation Ordered Access = not supported",
            Verbosity::Error,
        );
        return Err(InitializeError(
            "Presentation Ordered Access = not supported".to_string(),
        ));
    }
    if let Some(access_scope) = options.access_scope {
        if access_scope != AccessScope::I {
            logger.log_message(
                "    Presentation Access Scope = not supported",
                Verbosity::Error,
            );
            return Err(InitializeError(
                "Presentation Access Scope = not supported".to_string(),
            ));
        }
    }

    let publisher_qos = QosKind::Specific(PublisherQos {
        partition: options.partition_qos_policy(),
        ..Default::default()
    });
    let publisher = participant.create_publisher(publisher_qos, NO_LISTENER, NO_STATUS)?;

    let base_topic_name = options.topic_name.as_ref().unwrap();
    let base_color = options.color.as_deref().unwrap_or("BLUE");

    let mut data_writers = Vec::with_capacity(options.num_topics as usize);

    for i in 0..options.num_topics {
        let topic_name = format!(
            "{}{}",
            base_topic_name,
            if i > 0 { i.to_string() } else { "".to_string() }
        );

        let topic = participant
            .find_topic::<ShapeType>(&topic_name, Duration::new(0, 0))
            .expect("topic exists");

        println!(
            "Create writer for topic: {} color: {}",
            topic_name, base_color
        );

        let mut data_writer_qos = DataWriterQos {
            durability: options.durability_qos_policy(),
            reliability: options.reliability_qos_policy(),
            representation: options.data_representation_qos_policy(),
            ownership: options.ownership_qos_policy(),
            history: options.history_depth_qos_policy(),
            ..Default::default()
        };
        if options.deadline_interval > 0 {
            data_writer_qos.deadline.period = DurationKind::Finite(
                core::time::Duration::from_millis(options.deadline_interval).into(),
            );
        }
        if let Some(lifespan) = options.lifespan {
            if lifespan > 0 {
                data_writer_qos.lifespan.duration =
                    DurationKind::Finite(core::time::Duration::from_millis(lifespan).into());
            }
        }
        if options.ownership_qos_policy().kind == OwnershipQosPolicyKind::Exclusive {
            data_writer_qos.ownership_strength = options.ownership_strength_qos_policy();
        }
        if let Some(FinalInstanceState::U) = options.final_instance_state {
            data_writer_qos.writer_data_lifecycle.autodispose_unregistered_instances = false;
        }

        let data_writer = publisher.create_datawriter::<ShapeType>(
            &topic,
            QosKind::Specific(data_writer_qos),
            NO_LISTENER,
            NO_STATUS,
        )?;

        data_writers.push(data_writer);
    }

    Ok(data_writers)
}

fn run_publisher(
    data_writers: &[DataWriter<ShapeType>],
    options: &Options,
    logger: &Logger,
    all_done: Receiver<()>,
) -> Result<(), RunningError> {
    logger.log_message("Running run_publisher() function", Verbosity::Debug);

    let mut random_gen = thread_rng();

    let da_width = 240;
    let da_height = 270;
    let base_color = options.color.as_deref().unwrap_or("BLUE");

    let mut shape = ShapeType {
        color: base_color.to_string(),
        x: (random::<u32>() as i32).abs() % da_width,
        y: (random::<u32>() as i32).abs() % da_height,
        shapesize: options.shapesize,
        additional_payload_size: if options.additional_payload_size > 0 {
            vec![255; options.additional_payload_size]
        } else {
            vec![]
        },
    };

    // get random non-zero velocity.
    let mut x_vel = if random() {
        random_gen.gen_range(1..=5)
    } else {
        random_gen.gen_range(-5..=-1)
    };
    let mut y_vel = if random() {
        random_gen.gen_range(1..=5)
    } else {
        random_gen.gen_range(-5..=-1)
    };

    let mut n: u32 = 0;

    while all_done.try_recv().is_err() {
        move_shape(&mut shape, &mut x_vel, &mut y_vel, da_width, da_height);

        if options.shapesize == 0 {
            if let Some(size_modulo) = options.size_modulo {
                if size_modulo > 0 {
                    // Size cannot be 0, so increase it after modulo operation
                    shape.shapesize = (shape.shapesize % size_modulo) + 1;
                } else {
                    shape.shapesize += 1;
                }
            } else {
                shape.shapesize += 1;
            }
        }

        for (i, data_writer) in data_writers.iter().enumerate() {
            let topic_name = format!(
                "{}{}",
                options.topic_name.as_ref().unwrap(),
                if i > 0 { i.to_string() } else { "".to_string() }
            );

            for j in 0..options.num_instances {
                let instance_color = format!(
                    "{}{}",
                    base_color,
                    if j > 0 { j.to_string() } else { "".to_string() }
                );
                shape.color = instance_color;

                data_writer.write(shape.clone(), None).ok();

                if options.print_writer_samples {
                    print!(
                        "{:<10} {:<10} {:03} {:03} [{}]",
                        topic_name, shape.color, shape.x, shape.y, shape.shapesize
                    );
                    if options.additional_payload_size > 0 {
                        print!(" {{{}}}", shape.additional_payload_size.last().unwrap());
                    }
                    println!();
                }
            }
        }

        std::thread::sleep(std::time::Duration::from_millis(options.write_period_ms));

        n += 1;
        logger.log_message(format!("Publisher iteration: <{}>", n), Verbosity::Debug);
        logger.log_message(
            format!("Max number of iterations <{}>", options.num_iterations),
            Verbosity::Debug,
        );

        if options.num_iterations != 0 && n >= options.num_iterations {
            break;
        }
    }

    // Unregister or dispose instances of all DataWriters
    if let Some(final_state) = options.final_instance_state {
        for data_writer in data_writers.iter() {
            for j in 0..options.num_instances {
                let instance_color = format!(
                    "{}{}",
                    base_color,
                    if j > 0 { j.to_string() } else { "".to_string() }
                );
                shape.color = instance_color;

                match final_state {
                    FinalInstanceState::U => {
                        data_writer.unregister_instance(shape.clone(), None).ok();
                    }
                    FinalInstanceState::D => {
                        data_writer.dispose(shape.clone(), None).ok();
                    }
                }
            }
        }
    }

    for data_writer in data_writers.iter() {
        data_writer
            .wait_for_acknowledgments(dust_dds::infrastructure::time::Duration::new(1, 0))
            .ok();
    }

    Ok(())
}

fn init_subscriber(
    participant: &DomainParticipant,
    options: &Options,
    logger: &Logger,
) -> Result<Vec<DataReader<ShapeType>>, InitializeError> {
    logger.log_message("Running init_subscriber() function", Verbosity::Debug);

    if options.coherent {
        logger.log_message(
            "    Presentation Coherent Access = not supported",
            Verbosity::Error,
        );
        return Err(InitializeError(
            "Presentation Coherent Access = not supported".to_string(),
        ));
    }
    if options.ordered {
        logger.log_message(
            "    Presentation Ordered Access = not supported",
            Verbosity::Error,
        );
        return Err(InitializeError(
            "Presentation Ordered Access = not supported".to_string(),
        ));
    }
    if let Some(access_scope) = options.access_scope {
        if access_scope != AccessScope::I {
            logger.log_message(
                "    Presentation Access Scope = not supported",
                Verbosity::Error,
            );
            return Err(InitializeError(
                "Presentation Access Scope = not supported".to_string(),
            ));
        }
    }

    let subscriber_qos = QosKind::Specific(SubscriberQos {
        partition: options.partition_qos_policy(),
        ..Default::default()
    });
    let subscriber = participant.create_subscriber(subscriber_qos, NO_LISTENER, NO_STATUS)?;

    let base_topic_name = options.topic_name.as_ref().unwrap();
    let mut data_readers = Vec::with_capacity(options.num_topics as usize);

    for i in 0..options.num_topics {
        let topic_name = format!(
            "{}{}",
            base_topic_name,
            if i > 0 { i.to_string() } else { "".to_string() }
        );

        let topic = participant
            .find_topic::<ShapeType>(&topic_name, Duration::new(0, 0))
            .expect("topic exists");

        let mut data_reader_qos = DataReaderQos {
            durability: options.durability_qos_policy(),
            reliability: options.reliability_qos_policy(),
            representation: options.data_representation_qos_policy(),
            ownership: options.ownership_qos_policy(),
            history: options.history_depth_qos_policy(),
            ..Default::default()
        };
        if options.deadline_interval > 0 {
            data_reader_qos.deadline.period = DurationKind::Finite(
                core::time::Duration::from_millis(options.deadline_interval).into(),
            );
        }
        if let Some(time_filter) = options.time_filter {
            if time_filter > 0 {
                data_reader_qos.time_based_filter.minimum_separation =
                    DurationKind::Finite(core::time::Duration::from_millis(time_filter).into());
            }
        }

        if options.cft_expression.is_some() || options.color.is_some() {
            let filtered_topic_name = format!("{}_filtered", topic_name);

            let (filter_expr, cf_params) = if let Some(cft_expr) = &options.cft_expression {
                logger.log_message(
                    format!("    ContentFilterTopic = \"{}\"", cft_expr),
                    Verbosity::Debug,
                );
                (cft_expr.clone(), vec![])
            } else if let Some(color) = &options.color {
                let expr = "color = %0".to_string();
                logger.log_message(
                    format!("    ContentFilterTopic = \"color = '{}'\"", color),
                    Verbosity::Debug,
                );
                (expr, vec![color.clone()])
            } else {
                unreachable!()
            };

            let content_filtered_topic = participant.create_contentfilteredtopic(
                &filtered_topic_name,
                &topic,
                filter_expr,
                cf_params,
            )?;

            println!("Create reader for topic: {}", filtered_topic_name);
            let reader = subscriber.create_datareader::<ShapeType>(
                &content_filtered_topic,
                QosKind::Specific(data_reader_qos),
                NO_LISTENER,
                NO_STATUS,
            )?;
            data_readers.push(reader);
        } else {
            println!("Create reader for topic: {}", topic_name);
            let reader = subscriber.create_datareader::<ShapeType>(
                &topic,
                QosKind::Specific(data_reader_qos),
                NO_LISTENER,
                NO_STATUS,
            )?;
            data_readers.push(reader);
        }
    }

    Ok(data_readers)
}

fn run_subscriber(
    data_readers: &[DataReader<ShapeType>],
    options: &Options,
    logger: &Logger,
    all_done: Receiver<()>,
) -> Result<(), RunningError> {
    logger.log_message("Running run_subscriber() function", Verbosity::Debug);

    let mut instance_handle_color: HashMap<InstanceHandle, String> = HashMap::new();
    let mut previous_handles: Vec<Option<InstanceHandle>> = vec![None; options.num_topics as usize];
    let mut n: u32 = 0;

    while all_done.try_recv().is_err() {
        for (i, data_reader) in data_readers.iter().enumerate() {
            previous_handles[i] = None;
            loop {
                let max_samples = i32::MAX;
                let read_result = if !options.use_read {
                    if !options.take_read {
                        data_reader.take_next_instance(
                            max_samples,
                            previous_handles[i],
                            ANY_SAMPLE_STATE,
                            ANY_VIEW_STATE,
                            ANY_INSTANCE_STATE,
                        )
                    } else {
                        data_reader.take(
                            max_samples,
                            ANY_SAMPLE_STATE,
                            ANY_VIEW_STATE,
                            ANY_INSTANCE_STATE,
                        )
                    }
                } else {
                    if !options.take_read {
                        data_reader.read_next_instance(
                            max_samples,
                            previous_handles[i],
                            ANY_SAMPLE_STATE,
                            ANY_VIEW_STATE,
                            ANY_INSTANCE_STATE,
                        )
                    } else {
                        data_reader.read(
                            max_samples,
                            ANY_SAMPLE_STATE,
                            ANY_VIEW_STATE,
                            ANY_INSTANCE_STATE,
                        )
                    }
                };

                match read_result {
                    Ok(samples) => {
                        let topic_desc_name = dust_dds::topic_definition::topic_description::TopicDescription::get_name(&data_reader.get_topicdescription());

                        for sample in samples {
                            if sample.sample_info.valid_data {
                                let sample_data = sample.data.as_ref().expect("data present");
                                print!(
                                    "{:<10} {:<10} {:03} {:03} [{}]",
                                    topic_desc_name,
                                    sample_data.color,
                                    sample_data.x,
                                    sample_data.y,
                                    sample_data.shapesize
                                );
                                if !sample_data.additional_payload_size.is_empty() {
                                    print!(
                                        " {{{}}}",
                                        sample_data.additional_payload_size.last().unwrap()
                                    );
                                }
                                println!();
                                std::io::stdout().flush().expect("flush stdout succeeds");

                                instance_handle_color.insert(
                                    sample.sample_info.instance_handle,
                                    sample_data.color.clone(),
                                );
                            }

                            if sample.sample_info.instance_state != InstanceStateKind::Alive {
                                let color = instance_handle_color
                                    .get(&sample.sample_info.instance_handle)
                                    .map(|s| s.as_str())
                                    .unwrap_or("");

                                if sample.sample_info.instance_state
                                    == InstanceStateKind::NotAliveNoWriters
                                {
                                    println!(
                                        "{:<10} {:<10} NOT_ALIVE_NO_WRITERS_INSTANCE_STATE",
                                        topic_desc_name, color
                                    );
                                } else if sample.sample_info.instance_state
                                    == InstanceStateKind::NotAliveDisposed
                                {
                                    println!(
                                        "{:<10} {:<10} NOT_ALIVE_DISPOSED_INSTANCE_STATE",
                                        topic_desc_name, color
                                    );
                                }
                                std::io::stdout().flush().expect("flush stdout succeeds");
                            }

                            previous_handles[i] = Some(sample.sample_info.instance_handle);
                        }
                    }
                    Err(_) => break,
                }
            }
        }

        n += 1;
        logger.log_message(format!("Subscriber iteration: <{}>", n), Verbosity::Debug);
        logger.log_message(
            format!("Max number of iterations <{}>", options.num_iterations),
            Verbosity::Debug,
        );

        if options.num_iterations != 0 && n >= options.num_iterations {
            break;
        }

        std::thread::sleep(std::time::Duration::from_millis(options.read_period_ms));
    }

    Ok(())
}

fn initialize(options: &Options, logger: &Logger) -> Result<DomainParticipant, InitializeError> {
    logger.log_message("Running initialize() function", Verbosity::Debug);

    if options.datafrag_size > 0 {
        logger.log_message(
            format!(
                "Error configuring Data Fragmentation Size = {}",
                options.datafrag_size
            ),
            Verbosity::Error,
        );
        return Err(InitializeError(format!(
            "Error configuring Data Fragmentation Size = {}",
            options.datafrag_size
        )));
    }

    let participant_factory = DomainParticipantFactory::get_instance();

    if options.periodic_announcement > 0 {
        let configuration = DustDdsConfigurationBuilder::new()
            .participant_announcement_interval(std::time::Duration::from_millis(
                options.periodic_announcement,
            ))
            .build()?;
        *participant_factory.get_mut_configuration() = configuration;
    }

    let participant = participant_factory.create_participant(
        options.domain_id,
        QosKind::Default,
        Some(Listener),
        &[
            StatusKind::InconsistentTopic,
            StatusKind::OfferedIncompatibleQos,
            StatusKind::PublicationMatched,
            StatusKind::OfferedDeadlineMissed,
            StatusKind::LivelinessLost,
            StatusKind::RequestedIncompatibleQos,
            StatusKind::SubscriptionMatched,
            StatusKind::RequestedDeadlineMissed,
            StatusKind::LivelinessChanged,
        ],
    )?;

    let base_topic_name = options.topic_name.as_ref().unwrap();
    for i in 0..options.num_topics {
        let topic_name = format!(
            "{}{}",
            base_topic_name,
            if i > 0 { i.to_string() } else { "".to_string() }
        );
        println!("Create topic: {}", topic_name);
        let _topic = participant.create_topic::<ShapeType>(
            &topic_name,
            "ShapeType",
            QosKind::Default,
            NO_LISTENER,
            NO_STATUS,
        )?;
    }

    Ok(participant)
}

struct ParsingError;
struct InitializeError(String);
struct RunningError(String);

impl From<DdsError> for InitializeError {
    fn from(value: DdsError) -> Self {
        Self(format!("DdsError: {:?}", value))
    }
}
impl From<DdsError> for RunningError {
    fn from(value: DdsError) -> Self {
        Self(format!("DdsError: {:?}", value))
    }
}

struct Return {
    code: u8,
    description: String,
}
impl Debug for Return {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_fmt(format_args!("code {}: {}", self.code, self.description))
    }
}

impl Termination for Return {
    fn report(self) -> ExitCode {
        self.code.into()
    }
}

impl From<ParsingError> for Return {
    fn from(_: ParsingError) -> Self {
        Self {
            code: 1,
            description: String::new(),
        }
    }
}

impl From<InitializeError> for Return {
    fn from(value: InitializeError) -> Self {
        Self {
            code: 2,
            description: value.0,
        }
    }
}

impl From<RunningError> for Return {
    fn from(value: RunningError) -> Self {
        Self {
            code: 3,
            description: value.0,
        }
    }
}

fn run_app() -> Result<(), Return> {
    let (tx, rx) = std::sync::mpsc::channel();

    ctrlc::set_handler(move || {
        tx.send(()).ok();
    })
    .expect("Error setting Ctrl-C handler");

    let mut options = Options::parse();
    let logger = Logger::new(options.verbosity());

    logger.log_message("Parsing command line parameters...", Verbosity::Debug);
    options.validate(&logger)?;

    options.print_debug_options(&logger);

    logger.log_message("Initializing ShapeApp...", Verbosity::Debug);
    let participant = initialize(&options, &logger)?;

    logger.log_message("Running ShapeApp...", Verbosity::Debug);
    if options.publish {
        let data_writers = init_publisher(&participant, &options, &logger)?;
        run_publisher(&data_writers, &options, &logger, rx)?;
    } else {
        let data_readers = init_subscriber(&participant, &options, &logger)?;
        run_subscriber(&data_readers, &options, &logger, rx)?;
    }

    participant
        .delete_contained_entities()
        .expect("Entities being deleted");
    std::thread::sleep(std::time::Duration::from_millis(500));
    println!("Done.");
    Ok(())
}

fn main() -> ExitCode {
    match run_app() {
        Ok(()) => ExitCode::SUCCESS,
        Err(r) => ExitCode::from(r.code),
    }
}
