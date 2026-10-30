#![allow(dead_code)]

use std::io::Write;
use std::process;
use std::sync::{Arc, OnceLock};
use std::time::Duration as StdDuration;

// Print a line and flush stdout immediately.
macro_rules! println_flush {
    ($($arg:tt)*) => {{
        println!($($arg)*);
        let _ = std::io::stdout().flush();
    }};
}

use clap::{Parser, ValueEnum};

use int2dds::core::types::LENGTH_UNLIMITED;
use int2dds::dcps::infrastructure::qos_policy::OwnershipStrengthQosPolicy;
use int2dds::{
    common::instance_handle::InstanceHandle,
    core::{error::DdsError, time::Duration},
    domain::{domain_participant_factory::DomainParticipantFactory, qos::DomainParticipantQos},
    infrastructure::{
        qos_policy::{
            DataFragQosPolicy, DataRepresentationId, DataRepresentationQosPolicy, DeadlineQosPolicy,
            DurabilityQosPolicy, DurabilityQosPolicyKind, HistoryQosPolicy, HistoryQosPolicyKind,
            LifespanQosPolicy, OwnershipQosPolicy, OwnershipQosPolicyKind, PartitionQosPolicy,
            PresentationQosAccessScopeKind, ReliabilityQosPolicy,
            ReliabilityQosPolicyKind,
            TimeBasedFilterQosPolicy,
        },
        status::StatusMask,
    },
    publication::{
        data_writer_listener::DataWriterListener,
        qos::{DataWriterQos, PublisherQos},
    },
    subscription::{
        data_reader_listener::DataReaderListener,
        qos::{DataReaderQos, SubscriberQos},
        sample_info::{InstanceStateKind, SampleStateKind, ViewStateKind},
    },
    topic::{qos::TopicQos, topic_listener::TopicListener, type_support::DdsType},
};

#[derive(DdsType)]
#[dds_type(crate_path = "int2dds", extensibility = "Appendable")]
struct ShapeType {
    #[dds(key, bound = 128)]
    color: String,
    x: i32,
    y: i32,
    shapesize: i32,
    #[dds(uint8)]
    additional_payload_size: Vec<u8>,
}

#[derive(Debug, Clone, Copy, PartialEq, ValueEnum)]
enum Verbosity {
    #[value(name = "e")]
    Error = 1,
    #[value(name = "d")]
    Debug = 2,
}

struct Logger {
    verbosity: Verbosity,
}

impl Logger {
    fn new(verbosity: Verbosity) -> Self {
        Self { verbosity }
    }

    fn log_message(&self, message: &str, level: Verbosity) {
        if level as i32 <= self.verbosity as i32 {
            println_flush!("{}", message);
        }
    }

    fn set_verbosity(&mut self, verbosity: Verbosity) {
        self.verbosity = verbosity;
    }
}

static LOGGER: OnceLock<Logger> = OnceLock::new();

fn init_logger(verbosity: Verbosity) {
    let _ = LOGGER.set(Logger::new(verbosity));
}

fn get_logger() -> &'static Logger {
    LOGGER.get().expect("Logger not initialized")
}

struct QosUtils;

impl QosUtils {
    fn get_reliability_policy(options: &ShapeOptions) -> ReliabilityQosPolicy {
        ReliabilityQosPolicy {
            kind: if options.best_effort {
                ReliabilityQosPolicyKind::BestEffort
            } else {
                ReliabilityQosPolicyKind::Reliable
            },
            max_blocking_time: Duration { sec: 0, nanosec: 100_000_000 },
        }
    }

    fn get_durability_policy(options: &ShapeOptions) -> DurabilityQosPolicy {
        DurabilityQosPolicy {
            kind: match options.durability.chars().next().unwrap_or('v') {
                'v' => DurabilityQosPolicyKind::Volatile,
                'l' => DurabilityQosPolicyKind::TransientLocal,
                't' => DurabilityQosPolicyKind::Transient,
                'p' => DurabilityQosPolicyKind::Persistent,
                _ => DurabilityQosPolicyKind::Volatile,
            },
        }
    }

    fn get_ownership_policy(options: &ShapeOptions) -> OwnershipQosPolicy {
        OwnershipQosPolicy {
            kind: if options.ownership_strength != -1 {
                OwnershipQosPolicyKind::Exclusive
            } else {
                OwnershipQosPolicyKind::Shared
            },
        }
    }

    fn get_ownership_strength_policy(options: &ShapeOptions) -> OwnershipStrengthQosPolicy {
        OwnershipStrengthQosPolicy {
            value: if options.ownership_strength != -1 {
                options.ownership_strength
            } else {
                0 // Default value for shared ownership
            },
        }
    }

    fn get_history_policy(options: &ShapeOptions) -> HistoryQosPolicy {
        HistoryQosPolicy {
            kind: match options.history_depth {
                depth if depth > 0 => HistoryQosPolicyKind::KeepLast(depth),
                0 => HistoryQosPolicyKind::KeepAll,
                _ => HistoryQosPolicyKind::default(),
            },
            ..Default::default()
        }
    }

    fn get_access_scope_kind(options: &ShapeOptions) -> PresentationQosAccessScopeKind {
        match options.access_scope.as_deref() {
            Some("i") | Some("instance") => PresentationQosAccessScopeKind::Instance,
            Some("t") | Some("topic") => PresentationQosAccessScopeKind::Topic,
            Some("g") | Some("group") => PresentationQosAccessScopeKind::Group,
            _ => PresentationQosAccessScopeKind::Instance,
        }
    }

    fn get_deadline_policy(options: &ShapeOptions) -> DeadlineQosPolicy {
        if options.deadline_interval == 0 {
            DeadlineQosPolicy::default()
        } else {
            DeadlineQosPolicy { period: Duration::from_millis(options.deadline_interval as i64) }
        }
    }

    fn get_lifespan_policy(options: &ShapeOptions) -> LifespanQosPolicy {
        if options.lifespan > 0 {
            LifespanQosPolicy {
                duration: Duration {
                    sec: (options.get_lifespan_us() / 1_000_000) as i32,
                    nanosec: ((options.get_lifespan_us() % 1_000_000) * 1_000) as u32,
                },
            }
        } else {
            LifespanQosPolicy::default() // infinite
        }
    }

    fn get_time_based_filter_policy(options: &ShapeOptions) -> TimeBasedFilterQosPolicy {
        let time_filter_us = options.get_time_filter_us();
        if time_filter_us > 0 {
            TimeBasedFilterQosPolicy {
                minimum_separation: Duration {
                    sec: (time_filter_us / 1_000_000) as i32,
                    nanosec: ((time_filter_us % 1_000_000) * 1_000) as u32,
                },
            }
        } else {
            TimeBasedFilterQosPolicy::default() // no filter
        }
    }

    fn get_data_representation_policy(options: &ShapeOptions) -> DataRepresentationQosPolicy {
        match options.data_representation {
            1 => DataRepresentationQosPolicy {
                value: vec![DataRepresentationId::XcdrDataRepresentation],
            },
            2 => DataRepresentationQosPolicy {
                value: vec![DataRepresentationId::Xcdr2DataRepresentation],
            },
            _ => DataRepresentationQosPolicy {
                value: vec![DataRepresentationId::XcdrDataRepresentation],
            }, // default to XCDR
        }
    }
    fn reliability_to_string(kind: ReliabilityQosPolicyKind) -> String {
        match kind {
            ReliabilityQosPolicyKind::BestEffort => "BEST_EFFORT".to_string(),
            ReliabilityQosPolicyKind::Reliable => "RELIABLE".to_string(),
        }
    }

    fn durability_to_string(kind: DurabilityQosPolicyKind) -> String {
        match kind {
            DurabilityQosPolicyKind::Volatile => "VOLATILE".to_string(),
            DurabilityQosPolicyKind::TransientLocal => "TRANSIENT_LOCAL".to_string(),
            DurabilityQosPolicyKind::Transient => "TRANSIENT".to_string(),
            DurabilityQosPolicyKind::Persistent => "PERSISTENT".to_string(),
        }
    }

    fn ownership_to_string(kind: OwnershipQosPolicyKind) -> String {
        match kind {
            OwnershipQosPolicyKind::Shared => "SHARED".to_string(),
            OwnershipQosPolicyKind::Exclusive => "EXCLUSIVE".to_string(),
        }
    }

    fn history_to_string(kind: HistoryQosPolicyKind) -> String {
        match kind {
            HistoryQosPolicyKind::KeepAll => "KEEP_ALL".to_string(),
            HistoryQosPolicyKind::KeepLast(_) => "KEEP_LAST".to_string(),
        }
    }

    fn access_scope_to_string(scope: PresentationQosAccessScopeKind) -> String {
        match scope {
            PresentationQosAccessScopeKind::Instance => "INSTANCE_PRESENTATION_QOS".to_string(),
            PresentationQosAccessScopeKind::Topic => "TOPIC_PRESENTATION_QOS".to_string(),
            PresentationQosAccessScopeKind::Group => "GROUP_PRESENTATION_QOS".to_string(),
        }
    }

    fn verbosity_to_string(verbosity: Verbosity) -> String {
        match verbosity {
            Verbosity::Error => "ERROR".to_string(),
            Verbosity::Debug => "DEBUG".to_string(),
        }
    }

    fn data_representation_to_string(policy: &DataRepresentationQosPolicy) -> String {
        if policy.value.is_empty() {
            return "XCDR".to_string(); // default
        }

        let mut representations = Vec::new();
        for repr in &policy.value {
            match repr {
                DataRepresentationId::XcdrDataRepresentation => representations.push("XCDR"),
                DataRepresentationId::Xcdr2DataRepresentation => representations.push("XCDR2"),
                DataRepresentationId::XmlDataRepresentation => representations.push("XML"),
            }
        }
        representations.join(", ")
    }

    fn data_representation_id_to_string(data_representation_value: DataRepresentationId) -> String {
        match data_representation_value {
            DataRepresentationId::XcdrDataRepresentation => "XCDR".to_string(),
            DataRepresentationId::Xcdr2DataRepresentation => "XCDR2".to_string(),
            DataRepresentationId::XmlDataRepresentation => "XML".to_string(),
        }
    }
}

/// DDS Shapes Demo Application
#[derive(Parser, Clone)]
#[command(author, version, about, long_about = None)]
#[command(allow_negative_numbers = true)]
struct ShapeOptions {
    /// Set log message verbosity
    #[arg(short = 'v', value_enum, default_value_t = Verbosity::Error)]
    verbosity: Verbosity,

    /// Publish samples
    #[arg(short = 'P', default_value_t = false)]
    publish: bool,

    /// Subscribe samples
    #[arg(short = 'S', default_value_t = false)]
    subscribe: bool,

    /// Domain id
    #[arg(short = 'd', default_value_t = 0)]
    domain_id: u32,

    /// BEST_EFFORT reliability
    #[arg(short = 'b', default_value_t = false)]
    best_effort: bool,

    /// RELIABLE reliability (default)
    #[arg(short = 'r', default_value_t = false)]
    reliable: bool,

    /// Keep history depth [0: KEEP_ALL]
    #[arg(short = 'k', default_value_t = -1)]
    history_depth: i32,

    /// Set a 'deadline' with interval (ms) [0: OFF]
    #[arg(short = 'f', default_value_t = 0)]
    deadline_interval: i32,

    /// Set ownership strength [-1: SHARED]
    #[arg(short = 's', default_value_t = -1)]
    ownership_strength: i32,

    /// Set the topic name
    #[arg(short = 't')]
    topic_name: Option<String>,

    /// Set color to publish (filter if subscriber)
    #[arg(short = 'c')]
    color: Option<String>,

    /// Set a 'partition' string
    #[arg(short = 'p')]
    partition: Option<String>,

    /// Set durability (v=volatile, l=transient-local, t=transient, p=persistent)
    #[arg(short = 'D', default_value = "v")]
    durability: String,

    /// Set data representation [1: XCDR, 2: XCDR2]
    #[arg(short = 'x', default_value_t = 1)]
    data_representation: u8,

    /// Print Publisher's samples
    #[arg(short = 'w', default_value_t = false)]
    print_writer_samples: bool,

    /// Set shapesize (0: increase the size for every sample)
    #[arg(short = 'z', default_value_t = 20)]
    shapesize: i32,

    /// Use 'read()' instead of 'take()'
    #[arg(short = 'R', default_value_t = false)]
    use_read: bool,

    /// Waiting period between 'write()' operations in ms
    #[arg(long = "write-period", default_value_t = 33)]
    write_period: u64,

    /// Waiting period between 'read()' or 'take()' operations in ms
    #[arg(long = "read-period", default_value_t = 100)]
    read_period: u64,

    /// Apply 'time based filter' with interval in ms [0: OFF]
    #[arg(long = "time-filter", default_value_t = 0)]
    time_filter: u64,

    /// Indicates the lifespan of a sample in ms
    #[arg(long = "lifespan", default_value_t = 0)]
    lifespan: u64,

    /// Number of iterations of the main loop. After that, the application will exit
    #[arg(long = "num-iterations", default_value_t = 0)]
    num_iterations: u32,

    /// Number of instances a DataWriter writes
    #[arg(long = "num-instances", default_value_t = 1)]
    num_instances: u32,

    /// Number of topics created (using the same type)
    #[arg(long = "num-topics", default_value_t = 1)]
    num_topics: u32,

    /// Action performed after the DataWriter finishes its execution (u=unregister, d=dispose)
    #[arg(long = "final-instance-state")]
    final_instance_state: Option<String>,

    /// Sets Presentation.access_scope to INSTANCE, TOPIC or GROUP (i=instance, t=topic, g=group)
    #[arg(long = "access-scope")]
    access_scope: Option<String>,

    /// Sets Presentation.coherent_access = true
    #[arg(long = "coherent", default_value_t = false)]
    coherent: bool,

    /// Sets Presentation.ordered_access = true
    #[arg(long = "ordered", default_value_t = false)]
    ordered: bool,

    /// Amount of samples sent for each DataWriter and instance that are grouped in a coherent set
    #[arg(long = "coherent-sample-count", default_value_t = 0)]
    coherent_sample_count: u32,

    /// Amount of bytes added to the samples written
    #[arg(long = "additional-payload-size", default_value_t = 0)]
    additional_payload_size: u32,

    /// Uses take()/read() instead of take_next_instance() read_next_instance()
    #[arg(long = "take-read", default_value_t = false)]
    take_read: bool,

    /// Periodic participant announcement period in ms. Default 0 (off)
    #[arg(long = "periodic-announcement", default_value_t = 0)]
    periodic_announcement: u64,

    /// Content filter expression (subscriber). Overrides default color filter.
    #[arg(long = "cft")]
    cft_expression: Option<String>,

    /// Publisher size modulo. shapesize cycles 1..=N (requires -z 0)
    #[arg(long = "size-modulo", default_value_t = 0)]
    size_modulo: u32,

    /// Set the data fragment size in bytes (default: 0, means not set)
    #[arg(long = "datafrag-size", default_value_t = 0)]
    datafrag_size: u32,

    /// Flag to track if access scope was explicitly set
    #[arg(skip)]
    coherent_set_access_scope_set: bool,
}

impl ShapeOptions {
    fn validate_and_postprocess(&mut self) -> Result<(), i32> {
        let logger = get_logger();

        // Validation
        if self.topic_name.is_none() {
            logger.log_message("please specify topic name [-t]", Verbosity::Error);
            return Err(1);
        }
        if !self.publish && !self.subscribe {
            logger.log_message("please specify publish [-P] or subscribe [-S]", Verbosity::Error);
            return Err(1);
        }
        if self.publish && self.subscribe {
            logger.log_message(
                "please specify only one of: publish [-P] or subscribe [-S]",
                Verbosity::Error,
            );
            return Err(1);
        }

        // Set default color for publisher if not specified
        if self.publish && self.color.is_none() {
            logger.log_message(
                "warning: color was not specified, defaulting to \"BLUE\"",
                Verbosity::Error,
            );
            self.color = Some("BLUE".to_string());
        }

        // --cft and -c cannot be specified together for the subscriber
        if self.subscribe && self.cft_expression.is_some() && self.color.is_some() {
            logger.log_message(
                "error: cannot specify both --cft and -c for subscriber applications",
                Verbosity::Error,
            );
            return Err(1);
        }

        // Validation for final instance state
        if let Some(state) = &self.final_instance_state {
            match state.as_str() {
                "u" | "unregister" => {}
                "d" | "dispose" => {}
                _ => {
                    logger.log_message(
                        &format!("Invalid final instance state: {}", state),
                        Verbosity::Error,
                    );
                    return Err(1);
                }
            }
        }

        // Validation for data representation
        match self.data_representation {
            1 | 2 => {} // Valid values: 1 = XCDR, 2 = XCDR2
            _ => {
                logger.log_message(
                    &format!(
                        "Invalid data representation: {}. Valid options are: 1 (XCDR), 2 (XCDR2)",
                        self.data_representation
                    ),
                    Verbosity::Error,
                );
                return Err(1);
            }
        }

        // Validation for durability: reject unrecognized values (empty keeps default)
        if let Some(c) = self.durability.chars().next() {
            if !matches!(c, 'v' | 'l' | 't' | 'p') {
                logger.log_message(
                    &format!("unrecognized value for durability {}", c),
                    Verbosity::Error,
                );
                return Err(1);
            }
        }

        // Reject fragment sizes above 65535 bytes
        if self.datafrag_size > 65535 {
            logger.log_message(
                &format!(
                    "incorrect value for datafrag-size, it must be <= 65535 bytes: {}",
                    self.datafrag_size
                ),
                Verbosity::Error,
            );
            return Err(1);
        }

        if self.coherent_sample_count == 1 {
            logger.log_message(
                &format!(
                    "incorrect value for coherent-sample-count, it must be >=2 {}",
                    self.coherent_sample_count
                ),
                Verbosity::Error,
            );
            return Err(1);
        }

        self.coherent_set_access_scope_set = self.access_scope.is_some();

        self.print_warnings(&logger);

        self.print_configuration(&logger);

        Ok(())
    }

    fn print_warnings(&self, logger: &Logger) {
        if self.publish && self.time_filter > 0 {
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
        if self.subscribe && self.lifespan > 0 {
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
        if self.subscribe && self.coherent_sample_count > 0 {
            logger.log_message(
                "warning: --coherent-sample-count ignored on subscriber applications",
                Verbosity::Error,
            );
        }
        if !self.coherent && !self.ordered && self.coherent_sample_count > 0 {
            logger.log_message("warning: --coherent-sample-count ignored because not coherent, or ordered access enabled", Verbosity::Error);
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
        if self.size_modulo > 0 && self.shapesize != 0 {
            logger.log_message(
                "warning: --size-modulo has no effect unless shapesize (-z) is set to 0",
                Verbosity::Error,
            );
        }
    }

    fn print_configuration(&self, logger: &Logger) {
        let app_kind = if self.publish { "publisher" } else { "subscriber" };
        let data_representation_policy = QosUtils::get_data_representation_policy(self);
        logger.log_message(&format!(
            "Shape Options: \n    Verbosity = {}\n    This application is a {}\n    DomainId = {}\n    ReliabilityKind = {}\n    DurabilityKind = {}\n    DataRepresentation = {}\n    HistoryDepth = {}\n    OwnershipStrength = {}\n    TimeBasedFilterInterval = {}ms\n    DeadlineInterval = {}ms\n    Shapesize = {}\n    Reading method = {}\n    Write period = {}ms\n    Read period = {}ms\n    Lifespan = {}ms\n    Number of iterations = {}\n    Number of instances = {}\n    Number of entities = {}\n    Coherent sets = {}\n    Ordered access = {}\n    Access Scope = {}\n    Coherent Sample Count = {}\n    Additional Payload Size = {}\n    Final Instance State = {}\n    Periodic Announcement Period = {}ms\n    Data Fragmentation Size = {} bytes",
            QosUtils::verbosity_to_string(logger.verbosity),
            app_kind,
            self.domain_id,
            QosUtils::reliability_to_string(QosUtils::get_reliability_policy(self).kind),
            QosUtils::durability_to_string(QosUtils::get_durability_policy(self).kind),
            QosUtils::data_representation_to_string(&data_representation_policy),
            self.history_depth,
            self.ownership_strength,
            self.time_filter,
            self.deadline_interval,
            self.shapesize,
            match (self.use_read, !self.take_read) {
                (false, true) => "take_next_instance",
                (false, false) => "take",
                (true, true) => "read_next_instance",
                (true, false) => "read",
            },
            self.write_period,
            self.read_period,
            self.lifespan,
            self.num_iterations,
            self.num_instances,
            self.num_topics,
            self.coherent,
            self.ordered,
            QosUtils::access_scope_to_string(QosUtils::get_access_scope_kind(self)),
            self.coherent_sample_count,
            self.additional_payload_size,
            self.get_final_instance_state_string(),
            self.periodic_announcement,
            self.datafrag_size
        ), Verbosity::Debug);

        if let Some(ref topic_name) = self.topic_name {
            logger.log_message(&format!("    Topic = {}", topic_name), Verbosity::Debug);
        }
        if let Some(ref color) = self.color {
            logger.log_message(&format!("    Color = {}", color), Verbosity::Debug);
        }
        if let Some(ref partition) = self.partition {
            logger.log_message(&format!("    Partition = {}", partition), Verbosity::Debug);
        }
    }

    fn get_final_instance_state_string(&self) -> String {
        match self.final_instance_state.as_deref() {
            Some("u") | Some("unregister") => "Unregister".to_string(),
            Some("d") | Some("dispose") => "Dispose".to_string(),
            _ => "not specified".to_string(),
        }
    }

    // Period options are in milliseconds. These return microseconds.
    fn get_write_period_us(&self) -> u64 {
        self.write_period * 1000
    }

    fn get_read_period_us(&self) -> u64 {
        self.read_period * 1000
    }

    fn get_time_filter_us(&self) -> u64 {
        self.time_filter * 1000
    }

    fn get_lifespan_us(&self) -> u64 {
        self.lifespan * 1000
    }

    fn get_periodic_announcement_us(&self) -> u64 {
        self.periodic_announcement * 1000
    }

    fn should_unregister(&self) -> bool {
        matches!(self.final_instance_state.as_deref(), Some("u") | Some("unregister"))
    }

    fn should_dispose(&self) -> bool {
        matches!(self.final_instance_state.as_deref(), Some("d") | Some("dispose"))
    }

    // Drawing area size and default velocity
    fn get_da_width(&self) -> i32 {
        240
    }
    fn get_da_height(&self) -> i32 {
        270
    }
    fn get_xvel(&self) -> i32 {
        3
    }
    fn get_yvel(&self) -> i32 {
        3
    }
}

struct PubListener;

impl DataWriterListener for PubListener {
    type Foo = ShapeType;

    fn on_offered_incompatible_qos(
        &self,
        writer: &int2dds::publication::data_writer::DataWriter<Self::Foo>,
        status: &int2dds::infrastructure::status::OfferedIncompatibleQosStatus,
    ) {
        let topic = writer.get_topic().unwrap();
        let topic_name = topic.get_name();
        let type_name = topic.get_type_name();
        println_flush!(
            "on_offered_incompatible_qos() topic: '{}'  type: '{}' : {:?} ({})",
            topic_name,
            type_name,
            status.last_policy_id(),
            status.last_policy_id().as_str()
        );
    }

    fn on_publication_matched(
        &self,
        writer: &int2dds::publication::data_writer::DataWriter<Self::Foo>,
        status: &int2dds::infrastructure::status::PublicationMatchedStatus,
    ) {
        let topic = writer.get_topic().unwrap();
        let topic_name = topic.get_name();
        let type_name = topic.get_type_name();
        println_flush!(
            "on_publication_matched() topic: '{}'  type: '{}' : matched readers {} (change = {})",
            topic_name,
            type_name,
            status.current_count(),
            status.current_count_change()
        );
    }

    fn on_offered_deadline_missed(
        &self,
        writer: &int2dds::publication::data_writer::DataWriter<Self::Foo>,
        status: &int2dds::infrastructure::status::OfferedDeadlineMissedStatus,
    ) {
        let topic = writer.get_topic().unwrap();
        let topic_name = topic.get_name();
        let type_name = topic.get_type_name();
        println_flush!(
            "on_offered_deadline_missed() topic: '{}'  type: '{}' : (total = {}, change = {})",
            topic_name,
            type_name,
            status.total_count(),
            status.total_count_change()
        );
    }

    fn on_liveliness_lost(
        &self,
        writer: &int2dds::publication::data_writer::DataWriter<Self::Foo>,
        status: &int2dds::infrastructure::status::LivelinessLostStatus,
    ) {
        let topic = writer.get_topic().unwrap();
        let topic_name = topic.get_name();
        let type_name = topic.get_type_name();
        println_flush!(
            "on_liveliness_lost() topic: '{}'  type: '{}' : (total = {}, change = {})",
            topic_name,
            type_name,
            status.total_count(),
            status.total_count_change()
        );
    }
}

struct SubListener;

impl DataReaderListener for SubListener {
    type Foo = ShapeType;

    fn on_requested_incompatible_qos(
        &self,
        reader: &int2dds::subscription::data_reader::DataReader<Self::Foo>,
        status: &int2dds::infrastructure::status::RequestedIncompatibleQosStatus,
    ) {
        let topic_description = reader.get_topicdescription().unwrap();
        let topic_name = topic_description.get_name();
        let type_name = topic_description.get_type_name();
        println_flush!(
            "on_requested_incompatible_qos() topic: '{}'  type: '{}' : {:?} ({})",
            topic_name,
            type_name,
            status.last_policy_id(),
            status.last_policy_id().as_str()
        );
    }

    fn on_subscription_matched(
        &self,
        reader: &int2dds::subscription::data_reader::DataReader<Self::Foo>,
        status: &int2dds::infrastructure::status::SubscriptionMatchedStatus,
    ) {
        let topic_description = reader.get_topicdescription().unwrap();
        let topic_name = topic_description.get_name();
        let type_name = topic_description.get_type_name();
        println_flush!(
            "on_subscription_matched() topic: '{}'  type: '{}' : matched writers {} (change = {})",
            topic_name,
            type_name,
            status.current_count(),
            status.current_count_change()
        );
    }

    fn on_requested_deadline_missed(
        &self,
        reader: &int2dds::subscription::data_reader::DataReader<Self::Foo>,
        status: &int2dds::infrastructure::status::RequestedDeadlineMissedStatus,
    ) {
        let topic_description = reader.get_topicdescription().unwrap();
        let topic_name = topic_description.get_name();
        let type_name = topic_description.get_type_name();
        println_flush!(
            "on_requested_deadline_missed() topic: '{}'  type: '{}' : (total = {}, change = {})",
            topic_name,
            type_name,
            status.total_count(),
            status.total_count_change()
        );
    }

    fn on_liveliness_changed(
        &self,
        reader: &int2dds::subscription::data_reader::DataReader<Self::Foo>,
        status: &int2dds::infrastructure::status::LivelinessChangedStatus,
    ) {
        let topic_description = reader.get_topicdescription().unwrap();
        let topic_name = topic_description.get_name();
        let type_name = topic_description.get_type_name();
        println_flush!(
            "on_liveliness_changed() topic: '{}'  type: '{}' : (alive = {}, not_alive = {})",
            topic_name,
            type_name,
            status.alive_count(),
            status.not_alive_count()
        );
    }
}

struct ShapeTopicListener;

impl TopicListener for ShapeTopicListener {
    fn on_inconsistent_topic(
        &self,
        topic: &int2dds::topic::topic::Topic,
        _status: &int2dds::infrastructure::status::InconsistentTopicStatus,
    ) {
        let topic_name = topic.get_name();
        let type_name = topic.get_type_name();
        println_flush!("on_inconsistent_topic() topic: '{}'  type: '{}'", topic_name, type_name);
    }
}

use std::sync::atomic::{AtomicBool, Ordering};

static SHOULD_EXIT: AtomicBool = AtomicBool::new(false);

fn install_signal_handlers() -> Result<(), Box<dyn std::error::Error>> {
    ctrlc::set_handler(move || {
        SHOULD_EXIT.store(true, Ordering::SeqCst);
    })?;
    Ok(())
}

struct ShapeApplication {
    participant: Option<Arc<int2dds::domain::domain_participant::DomainParticipant>>,
    topics: Vec<Arc<int2dds::topic::topic::Topic>>,
    publisher: Option<Arc<int2dds::publication::publisher::Publisher>>,
    subscriber: Option<Arc<int2dds::subscription::subscriber::Subscriber>>,
    data_writers: Vec<Arc<int2dds::publication::data_writer::DataWriter<ShapeType>>>,
    data_readers: Vec<Arc<int2dds::subscription::data_reader::DataReader<ShapeType>>>,
}

impl ShapeApplication {
    fn new() -> Self {
        Self {
            participant: None,
            topics: Vec::new(),
            publisher: None,
            subscriber: None,
            data_writers: Vec::new(),
            data_readers: Vec::new(),
        }
    }

    fn initialize(&mut self, options: &ShapeOptions) -> Result<(), DdsError> {
        let logger = get_logger();
        logger.log_message("Running initialize() function", Verbosity::Debug);

        let factory = DomainParticipantFactory::get_instance();
        let participant_qos = DomainParticipantQos::default();
        let participant = factory.create_participant(
            options.domain_id.try_into().unwrap(),
            participant_qos,
            None,
            StatusMask::default(),
        )?;
        let participant_arc = Arc::new(participant);
        self.participant = Some(participant_arc.clone());

        // Create topics
        let base_topic_name = options.topic_name.as_ref().unwrap();
        for i in 0..options.num_topics {
            let topic_name =
                if i == 0 { base_topic_name.clone() } else { format!("{}{}", base_topic_name, i) };
            println_flush!("Create topic: {}", topic_name);
            let topic_listener = ShapeTopicListener;
            let topic = participant_arc.create_topic::<ShapeType>(
                &topic_name,
                "ShapeType",
                TopicQos::default(),
                Some(Arc::new(topic_listener)),
                StatusMask::default(),
            )?;
            self.topics.push(Arc::new(topic));
        }

        if options.publish {
            self.init_publisher(options)?;
        } else {
            self.init_subscriber(options)?;
        }

        Ok(())
    }

    fn run(&self, options: &ShapeOptions) -> Result<(), DdsError> {
        let logger = get_logger();
        logger.log_message("Running run() function", Verbosity::Debug);

        if options.publish {
            self.run_publisher(options)
        } else {
            self.run_subscriber(options)
        }
    }

    fn cleanup(&mut self) -> Result<(), DdsError> {
        if let Some(participant_arc) = self.participant.take() {
            participant_arc.delete_contained_entities()?;

            self.data_writers.clear();
            self.data_readers.clear();
            self.publisher = None;
            self.subscriber = None;
            self.topics.clear();

            let participant = (*participant_arc).clone();
            drop(participant_arc);
            DomainParticipantFactory::get_instance().delete_participant(participant)?;
        }
        Ok(())
    }

    fn init_publisher(&mut self, options: &ShapeOptions) -> Result<(), DdsError> {
        let logger = get_logger();
        logger.log_message("Running init_publisher() function", Verbosity::Debug);

        let participant = self.participant.as_ref().unwrap();

        // Create publisher
        let mut publisher_qos = PublisherQos::default();
        if let Some(ref partition) = options.partition {
            publisher_qos.partition = PartitionQosPolicy { name: vec![partition.clone()] };
        }

        if options.coherent {
            publisher_qos.presentation.coherent_access = true;
        }
        if options.ordered {
            publisher_qos.presentation.ordered_access = true;
        }
        if options.coherent || options.ordered {
            publisher_qos.presentation.access_scope = QosUtils::get_access_scope_kind(options);
        }

        logger.log_message("Publisher QoS:", Verbosity::Debug);
        logger.log_message(
            &format!(
                "    Presentation Coherent Access = {}",
                publisher_qos.presentation.coherent_access
            ),
            Verbosity::Debug,
        );
        logger.log_message(
            &format!(
                "    Presentation Ordered Access = {}",
                publisher_qos.presentation.ordered_access
            ),
            Verbosity::Debug,
        );
        logger.log_message(
            &format!(
                "    Presentation Access Scope = {}",
                QosUtils::access_scope_to_string(publisher_qos.presentation.access_scope)
            ),
            Verbosity::Debug,
        );

        let publisher = participant.create_publisher(publisher_qos, None, StatusMask::default())?;
        let publisher_arc = Arc::new(publisher);
        self.publisher = Some(publisher_arc.clone());

        // Create data writers
        let mut writer_qos = DataWriterQos {
            reliability: QosUtils::get_reliability_policy(options),
            durability: QosUtils::get_durability_policy(options),
            ownership: QosUtils::get_ownership_policy(options),
            ownership_strength: QosUtils::get_ownership_strength_policy(options),
            history: QosUtils::get_history_policy(options),
            deadline: QosUtils::get_deadline_policy(options),
            lifespan: QosUtils::get_lifespan_policy(options),
            data_representation: QosUtils::get_data_representation_policy(options),
            ..DataWriterQos::default()
        };
        if options.should_unregister() {
            writer_qos.writer_data_lifecycle.autodispose_unregistered_instances = false;
        }
        // Per-writer RTPS DATA_FRAG fragment size.
        if options.datafrag_size > 0 {
            writer_qos.data_frag = DataFragQosPolicy { max_size: options.datafrag_size as i32 };
        }
        // Reliable writers send heartbeats standalone (periodic), not piggybacked.
        if writer_qos.reliability.kind == ReliabilityQosPolicyKind::Reliable {
            writer_qos.writer_reliability_extension.disable_piggyback_heartbeat = true;
            writer_qos.writer_reliability_extension.heartbeat_period = Duration::from_millis(100);
        }

        logger.log_message("Data Writer QoS:", Verbosity::Debug);
        logger.log_message(
            &format!(
                "    Reliability = {}",
                QosUtils::reliability_to_string(writer_qos.reliability.kind)
            ),
            Verbosity::Debug,
        );
        logger.log_message(
            &format!(
                "    Durability = {}",
                QosUtils::durability_to_string(writer_qos.durability.kind)
            ),
            Verbosity::Debug,
        );
        logger.log_message(
            &format!(
                "    Ownership = {}",
                QosUtils::ownership_to_string(writer_qos.ownership.kind)
            ),
            Verbosity::Debug,
        );
        logger.log_message(
            &format!("    History = {}", QosUtils::history_to_string(writer_qos.history.kind)),
            Verbosity::Debug,
        );

        for (_i, topic) in self.topics.iter().enumerate() {
            println_flush!(
                "Create writer for topic: {} color: {}",
                topic.get_name(),
                options.color.as_ref().unwrap()
            );
            let listener = PubListener;
            let writer = publisher_arc.create_datawriter::<ShapeType>(
                topic,
                writer_qos.clone(),
                Some(Arc::new(listener)),
                StatusMask::default(),
            )?;
            self.data_writers.push(Arc::new(writer));
        }

        Ok(())
    }

    fn init_subscriber(&mut self, options: &ShapeOptions) -> Result<(), DdsError> {
        let logger = get_logger();
        logger.log_message("Running init_subscriber() function", Verbosity::Debug);

        let participant = self.participant.as_ref().unwrap();

        // Create subscriber
        let mut subscriber_qos = SubscriberQos::default();
        if let Some(ref partition) = options.partition {
            subscriber_qos.partition = PartitionQosPolicy { name: vec![partition.to_owned()] };
        }

        if options.coherent {
            subscriber_qos.presentation.coherent_access = true;
        }
        if options.ordered {
            subscriber_qos.presentation.ordered_access = true;
        }
        if options.coherent || options.ordered {
            subscriber_qos.presentation.access_scope = QosUtils::get_access_scope_kind(options);
        }

        logger.log_message("Subscriber QoS:", Verbosity::Debug);
        logger.log_message(
            &format!(
                "    Presentation Coherent Access = {}",
                subscriber_qos.presentation.coherent_access
            ),
            Verbosity::Debug,
        );
        logger.log_message(
            &format!(
                "    Presentation Ordered Access = {}",
                subscriber_qos.presentation.ordered_access
            ),
            Verbosity::Debug,
        );
        logger.log_message(
            &format!(
                "    Presentation Access Scope = {}",
                QosUtils::access_scope_to_string(subscriber_qos.presentation.access_scope)
            ),
            Verbosity::Debug,
        );

        let subscriber =
            participant.create_subscriber(subscriber_qos, None, StatusMask::default())?;
        let subscriber_arc = Arc::new(subscriber);
        self.subscriber = Some(subscriber_arc.clone());

        // Create data readers
        let data_reader_qos = DataReaderQos {
            reliability: QosUtils::get_reliability_policy(options),
            durability: QosUtils::get_durability_policy(options),
            ownership: QosUtils::get_ownership_policy(options),
            history: QosUtils::get_history_policy(options),
            deadline: QosUtils::get_deadline_policy(options),
            data_representation: QosUtils::get_data_representation_policy(options),
            time_based_filter: QosUtils::get_time_based_filter_policy(options),
            ..DataReaderQos::default()
        };

        logger.log_message("Data Reader QoS:", Verbosity::Debug);
        logger.log_message(
            &format!(
                "    Reliability = {}",
                QosUtils::reliability_to_string(data_reader_qos.reliability.kind)
            ),
            Verbosity::Debug,
        );
        logger.log_message(
            &format!(
                "    Durability = {}",
                QosUtils::durability_to_string(data_reader_qos.durability.kind)
            ),
            Verbosity::Debug,
        );
        logger.log_message(
            &format!(
                "    Ownership = {}",
                QosUtils::ownership_to_string(data_reader_qos.ownership.kind)
            ),
            Verbosity::Debug,
        );
        logger.log_message(
            &format!("    History = {}", QosUtils::history_to_string(data_reader_qos.history.kind)),
            Verbosity::Debug,
        );

        if let Some(ref expr) = options.cft_expression {
            // Custom content filter expression with its parameters embedded in the expression
            for (i, topic) in self.topics.iter().enumerate() {
                let filtered_topic_name = format!(
                    "{}{}_filtered",
                    &topic.get_name(),
                    if i > 0 { i.to_string() } else { String::new() }
                );

                logger.log_message(
                    &format!("    ContentFilterTopic = \"{}\"", expr),
                    Verbosity::Debug,
                );

                let cft = participant
                    .create_contentfilteredtopic::<ShapeType>(
                        &filtered_topic_name,
                        &topic,
                        expr,
                        Vec::new(),
                    )
                    .map_err(|e| {
                        DdsError::Error(format!("Failed to create content filtered topic: {:?}", e))
                    })?;

                println_flush!("Create reader for topic: {} cft: \"{}\"", topic.get_name(), expr);

                let listener = SubListener;
                let reader = subscriber_arc
                    .create_datareader::<ShapeType>(
                        &cft,
                        data_reader_qos.clone(),
                        Some(Arc::new(listener)),
                        StatusMask::default(),
                    )
                    .map_err(|e| {
                        DdsError::Error(format!("Failed to create data reader: {:?}", e))
                    })?;

                self.data_readers.push(Arc::new(reader));
            }
        } else if let Some(ref color) = options.color {
            // Filter on the specified color with a content filtered topic
            for (i, topic) in self.topics.iter().enumerate() {
                let filtered_topic_name = format!(
                    "{}{}_filtered",
                    &topic.get_name(),
                    if i > 0 { i.to_string() } else { String::new() }
                );

                let parameter = format!("'{}'", color);

                logger.log_message(
                    &format!("    ContentFilterTopic = \"color = {}\"", parameter),
                    Verbosity::Debug,
                );

                let cft = participant
                    .create_contentfilteredtopic::<ShapeType>(
                        &filtered_topic_name,
                        &topic,
                        "color = %0",
                        vec![color.to_owned()],
                    )
                    .map_err(|e| {
                        DdsError::Error(format!("Failed to create content filtered topic: {:?}", e))
                    })?;

                println_flush!("Create reader for topic: {} color: {}", topic.get_name(), color);

                let listener = SubListener;
                let reader = subscriber_arc
                    .create_datareader::<ShapeType>(
                        &cft,
                        data_reader_qos.clone(),
                        Some(Arc::new(listener)),
                        StatusMask::default(),
                    )
                    .map_err(|e| {
                        DdsError::Error(format!("Failed to create data reader: {:?}", e))
                    })?;

                self.data_readers.push(Arc::new(reader));
            }
        } else {
            for topic in &self.topics {
                println_flush!("Create reader for topic: {}", topic.get_name());

                let listener = SubListener;
                let reader = subscriber_arc.create_datareader::<ShapeType>(
                    topic.as_ref(),
                    data_reader_qos.clone(),
                    Some(Arc::new(listener)),
                    StatusMask::default(),
                )?;
                self.data_readers.push(Arc::new(reader));
            }
        }

        logger.log_message("Data Reader created", Verbosity::Debug);

        Ok(())
    }

    fn run_publisher(&self, options: &ShapeOptions) -> Result<(), DdsError> {
        let logger = get_logger();
        logger.log_message("Running run_publisher() function", Verbosity::Debug);

        let publisher = self.publisher.as_ref().unwrap();
        let data_writers = &self.data_writers;

        logger.log_message("Data Writer created", Verbosity::Debug);
        logger.log_message(&format!("Color {}", options.color.as_ref().unwrap()), Verbosity::Debug);
        logger.log_message(&format!("xvel {}", options.get_xvel()), Verbosity::Debug);
        logger.log_message(&format!("yvel {}", options.get_yvel()), Verbosity::Debug);
        logger.log_message(&format!("da_width {}", options.get_da_width()), Verbosity::Debug);
        logger.log_message(&format!("da_height {}", options.get_da_height()), Verbosity::Debug);

        // Initialize shape
        let mut shape = ShapeType {
            color: options.color.clone().unwrap(),
            x: fastrand::i32(0..options.get_da_width()),
            y: fastrand::i32(0..options.get_da_height()),
            shapesize: options.shapesize,
            additional_payload_size: if options.additional_payload_size > 0 {
                vec![255u8; options.additional_payload_size as usize]
            } else {
                vec![]
            },
        };

        let mut xvel = ((fastrand::u32(0..5) + 1) as i32) * if fastrand::bool() { -1 } else { 1 };
        let mut yvel = ((fastrand::u32(0..5) + 1) as i32) * if fastrand::bool() { -1 } else { 1 };

        let mut n = 0;

        loop {
            // Move shape
            shape.x += xvel;
            shape.y += yvel;

            if shape.x < 0 {
                shape.x = 0;
                xvel = -xvel;
            }
            if shape.x > options.get_da_width() {
                shape.x = options.get_da_width();
                xvel = -xvel;
            }
            if shape.y < 0 {
                shape.y = 0;
                yvel = -yvel;
            }
            if shape.y > options.get_da_height() {
                shape.y = options.get_da_height();
                yvel = -yvel;
            }

            if options.shapesize == 0 {
                if options.size_modulo > 0 {
                    // Cycle 1..=size_modulo (size cannot be 0)
                    shape.shapesize = (shape.shapesize % options.size_modulo as i32) + 1;
                } else {
                    shape.shapesize += 1;
                }
            }

            if (options.coherent || options.ordered)
                && options.coherent_sample_count != 0
                && n % options.coherent_sample_count == 0
            {
                println_flush!("Started Coherent Set");
                let _ = publisher.begin_coherent_changes();
            }

            // Write one sample per instance on every writer
            for writer in data_writers {
                for j in 0..options.num_instances {
                    // Instances after the first append their index to the color
                    let instance_shape = ShapeType {
                        color: if options.num_instances > 1 && j > 0 {
                            format!("{}{}", options.color.as_ref().unwrap(), j)
                        } else {
                            options.color.clone().unwrap_or_else(|| "RED".to_string())
                        },
                        ..shape.clone()
                    };

                    writer.write(&instance_shape, InstanceHandle::NIL)?;

                    if options.print_writer_samples {
                        let additional_payload_info = if options.additional_payload_size > 0 {
                            format!(
                                " {{{}}}",
                                instance_shape.additional_payload_size.last().unwrap_or(&0)
                            )
                        } else {
                            String::new()
                        };

                        let topic = writer.get_topic()?;
                        let topic_name = topic.get_name();
                        let sanitized_topic = sanitize_xml_text(&topic_name);
                        let sanitized_color = sanitize_xml_text(&instance_shape.color);
                        println_flush!(
                            "{:<10} {:<10} {:03} {:03} [{}]{}",
                            sanitized_topic,
                            sanitized_color,
                            instance_shape.x,
                            instance_shape.y,
                            instance_shape.shapesize,
                            additional_payload_info
                        );
                    }
                }
            }

            if (options.coherent || options.ordered)
                && options.coherent_sample_count != 0
                && n % options.coherent_sample_count == options.coherent_sample_count - 1
            {
                println_flush!("Finished Coherent Set");
                let _ = publisher.end_coherent_changes();
            }

            std::thread::sleep(StdDuration::from_micros(options.get_write_period_us()));

            n += 1;
            logger.log_message(&format!("Publisher iteration: <{}>", n), Verbosity::Debug);
            logger.log_message(
                &format!("Max number of iterations <{}>", options.num_iterations),
                Verbosity::Debug,
            );

            if options.num_iterations != 0 && options.num_iterations <= n {
                break;
            }

            if SHOULD_EXIT.load(Ordering::SeqCst) {
                break;
            }
        }

        // Unregister or dispose each instance so that the subscriber observes the final state.
        if options.should_dispose() || options.should_unregister() {
            for writer in data_writers {
                for j in 0..options.num_instances {
                    let instance_shape = ShapeType {
                        color: if options.num_instances > 1 && j > 0 {
                            format!("{}{}", options.color.as_ref().unwrap(), j)
                        } else {
                            options.color.clone().unwrap()
                        },
                        ..shape.clone()
                    };
                    if options.should_dispose() {
                        writer.dispose(&instance_shape, InstanceHandle::NIL)?;
                    } else {
                        writer.unregister_instance(&instance_shape, InstanceHandle::NIL)?;
                    }
                }
            }
        }

        // Wait for acknowledgments so the subscriber has a chance to observe the final state.
        for writer in data_writers {
            let _ = writer.wait_for_acknowledgments(Duration { sec: 1, nanosec: 0 });
        }

        Ok(())
    }

    fn run_subscriber(&self, options: &ShapeOptions) -> Result<(), DdsError> {
        let logger = get_logger();
        logger.log_message("Running run_subscriber() function", Verbosity::Debug);

        let subscriber = self.subscriber.as_ref().ok_or(DdsError::PreconditionNotMet)?;
        let data_readers = &self.data_readers;

        let mut n = 0;

        loop {
            if options.coherent {
                println_flush!("Reading coherent sets, iteration {}", n);
            }
            if options.ordered {
                println_flush!("Reading with ordered access, iteration {}", n);
            }
            if options.coherent || options.ordered {
                let _ = subscriber.begin_access();
            }

            for reader in data_readers {
                let mut previous_handle = InstanceHandle::NIL;
                loop {
                    if SHOULD_EXIT.load(Ordering::SeqCst) {
                        break;
                    }
                    // --take-read selects take()/read() instead of the *_next_instance() variants
                    let use_next_instance = !options.take_read;
                    let log_msg = match (options.use_read, use_next_instance) {
                        (false, true) => "Calling take_next_instance() function",
                        (false, false) => "Calling take() function",
                        (true, true) => "Calling read_next_instance() function",
                        (true, false) => "Calling read() function",
                    };

                    logger.log_message(log_msg, Verbosity::Debug);

                    let result = match (options.use_read, use_next_instance) {
                        (false, true) => reader.take_next_instance(
                            LENGTH_UNLIMITED,
                            previous_handle,
                            &[SampleStateKind::ANY_SAMPLE_STATE],
                            &[ViewStateKind::ANY_VIEW_STATE],
                            &[InstanceStateKind::ANY_INSTANCE_STATE],
                        ),
                        (false, false) => reader.take(
                            LENGTH_UNLIMITED,
                            &[SampleStateKind::ANY_SAMPLE_STATE],
                            &[ViewStateKind::ANY_VIEW_STATE],
                            &[InstanceStateKind::ANY_INSTANCE_STATE],
                        ),
                        (true, true) => reader.read_next_instance(
                            LENGTH_UNLIMITED,
                            previous_handle,
                            &[SampleStateKind::ANY_SAMPLE_STATE],
                            &[ViewStateKind::ANY_VIEW_STATE],
                            &[InstanceStateKind::ANY_INSTANCE_STATE],
                        ),
                        (true, false) => reader.read(
                            LENGTH_UNLIMITED,
                            &[SampleStateKind::ANY_SAMPLE_STATE],
                            &[ViewStateKind::ANY_VIEW_STATE],
                            &[InstanceStateKind::ANY_INSTANCE_STATE],
                        ),
                    };

                    match result {
                        Ok(samples) => {
                            if samples.is_empty() {
                                break;
                            }

                            logger.log_message(
                                &format!("Read {} sample(s), printing them...", samples.len()),
                                Verbosity::Debug,
                            );

                            for (n_sample, sample) in samples.iter().enumerate() {
                                logger.log_message(
                                    &format!("Processing sample {}", n_sample),
                                    Verbosity::Debug,
                                );

                                let info = sample.sample_info();
                                let topic_description = reader.get_topicdescription()?;
                                let topic_name = topic_description.get_name();
                                let sanitized_topic = sanitize_xml_text(&topic_name);

                                if info.valid_data {
                                    let data = match sample.data() {
                                        Ok(d) => d,
                                        Err(e) => {
                                            logger.log_message(
                                                &format!(
                                                    "warning: deserialize failed: {}",
                                                    e
                                                ),
                                                Verbosity::Error,
                                            );
                                            continue;
                                        }
                                    };
                                    let sanitized_color = sanitize_xml_text(&data.color);
                                    println_flush!(
                                        "{:<10} {:<10} {:03} {:03} [{}]{}",
                                        sanitized_topic,
                                        sanitized_color,
                                        data.x,
                                        data.y,
                                        data.shapesize,
                                        if !data.additional_payload_size.is_empty() {
                                            format!(
                                                " {{{}}}",
                                                data.additional_payload_size.last().unwrap_or(&0)
                                            )
                                        } else {
                                            String::new()
                                        }
                                    );
                                }

                                if info.instance_state
                                    != InstanceStateKind::ALIVE_INSTANCE_STATE
                                {
                                    let color = reader
                                        .get_key_value(info.instance_handle)
                                        .map(|k| k.color)
                                        .unwrap_or_default();
                                    let sanitized_color = sanitize_xml_text(&color);
                                    match info.instance_state {
                                        InstanceStateKind::NOT_ALIVE_NO_WRITERS_INSTANCE_STATE => {
                                            println_flush!(
                                                "{:<10} {:<10} NOT_ALIVE_NO_WRITERS_INSTANCE_STATE",
                                                sanitized_topic, sanitized_color
                                            );
                                        }
                                        InstanceStateKind::NOT_ALIVE_DISPOSED_INSTANCE_STATE => {
                                            println_flush!(
                                                "{:<10} {:<10} NOT_ALIVE_DISPOSED_INSTANCE_STATE",
                                                sanitized_topic, sanitized_color
                                            );
                                        }
                                        _ => {}
                                    }
                                }
                            }

                            if let Some(first) = samples.first() {
                                previous_handle = first.sample_info().instance_handle;
                            }
                        }
                        Err(_) => break,
                    }
                }
            }

            if options.coherent || options.ordered {
                let _ = subscriber.end_access();
            }

            n += 1;
            logger.log_message(&format!("Subscriber iteration: <{}>", n), Verbosity::Debug);
            logger.log_message(
                &format!("Max number of iterations <{}>", options.num_iterations),
                Verbosity::Debug,
            );

            if options.num_iterations != 0 && options.num_iterations <= n {
                break;
            }

            if SHOULD_EXIT.load(Ordering::SeqCst) {
                break;
            }

            std::thread::sleep(StdDuration::from_micros(options.get_read_period_us()));
        }

        Ok(())
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let _ = install_signal_handlers();

    let mut options = ShapeOptions::parse();

    init_logger(options.verbosity);

    // Validate options and fill in defaults
    if let Err(code) = options.validate_and_postprocess() {
        process::exit(code);
    }

    let logger = get_logger();
    logger.log_message("Initializing ShapeApp...", Verbosity::Debug);

    let mut shape_app = ShapeApplication::new();

    if let Err(e) = shape_app.initialize(&options) {
        eprintln!("Error initializing application: {}", e);
        process::exit(2);
    }

    logger.log_message("Running ShapeApp...", Verbosity::Debug);

    shape_app.run(&options).unwrap_or_else(|e| {
        eprintln!("Error running application: {}", e);
        process::exit(3);
    });

    if let Err(e) = shape_app.cleanup() {
        eprintln!("Error during cleanup: {}", e);
    }

    println_flush!("Done.");
    Ok(())
}

use std::borrow::Cow;

fn sanitize_xml_text(input: &str) -> Cow<'_, str> {
    if input.chars().all(is_valid_xml_char) {
        Cow::Borrowed(input)
    } else {
        let mut sanitized = String::with_capacity(input.len());
        for ch in input.chars() {
            if is_valid_xml_char(ch) {
                sanitized.push(ch);
            }
        }
        Cow::Owned(sanitized)
    }
}

fn is_valid_xml_char(ch: char) -> bool {
    matches!(ch, '\u{9}' | '\u{A}' | '\u{D}' | '\u{20}'..='\u{D7FF}' | '\u{E000}'..='\u{FFFD}')
}
