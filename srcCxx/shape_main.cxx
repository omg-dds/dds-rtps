/****************************************************************
 * Use and redistribution is source and binary forms is permitted
 * subject to the OMG-DDS INTEROPERABILITY TESTING LICENSE found
 * at the following URL:
 *
 * https://github.com/omg-dds/dds-rtps/blob/master/LICENSE.md
 */
/****************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <ctype.h>
#include <time.h>
#include <signal.h>
#include <string.h>
#include <stdarg.h>
#include <iostream>

#if defined(RTI_CONNEXT_DDS)
#include "shape_configurator_rti_connext_dds.h"
#elif defined(TWINOAKS_COREDX)
#include "shape_configurator_toc_coredx_dds.h"
#elif defined(OPENDDS)
#include "shape_configurator_opendds.h"
#else
#error "Must define the DDS vendor"
#endif

#ifndef STRING_IN
#define STRING_IN
#endif
#ifndef STRING_INOUT
#define STRING_INOUT
#endif

using namespace DDS;



/*************************************************************/
int  all_done  = 0;

/*************************************************************/
void
handle_sig(int sig)
{
    if (sig == SIGINT) {
        all_done = 1;
    }
}

/*************************************************************/
int
install_sig_handlers()
{
    struct sigaction int_action;
    int_action.sa_handler = handle_sig;
    sigemptyset(&int_action.sa_mask);
    sigaddset(&int_action.sa_mask, SIGINT);
    int_action.sa_flags     = 0;
    sigaction(SIGINT,  &int_action, NULL);
    return 0;
}

enum Verbosity
{
    ERROR=1,
    DEBUG=2,
};

/*************************************************************/
class ShapeOptions {
public:
    DomainId_t                     domain_id;
    ReliabilityQosPolicyKind       reliability_kind;
    DurabilityQosPolicyKind        durability_kind;
    DataRepresentationId_t         data_representation;
    int                            history_depth;
    int                            ownership_strength;

    char               *topic_name;
    char               *color;
    char               *partition;

    bool                publish;
    bool                subscribe;

    int                 timebasedfilter_interval;
    int                 deadline_interval;

    int                 da_width;
    int                 da_height;

    int                 xvel;
    int                 yvel;
    int                 shapesize;

    Verbosity           verbosity;
    bool                print_writer_samples;

public:
    //-------------------------------------------------------------
    ShapeOptions()
    {
        domain_id           = 0;
        reliability_kind    = RELIABLE_RELIABILITY_QOS;
        durability_kind     = VOLATILE_DURABILITY_QOS;
        data_representation = XCDR_DATA_REPRESENTATION;
        history_depth       = -1;      /* means default */
        ownership_strength  = -1;      /* means shared */

        topic_name         = NULL;
        color              = NULL;
        partition          = NULL;

        publish            = false;
        subscribe          = false;

        timebasedfilter_interval = 0; /* off */
        deadline_interval        = 0; /* off */

        da_width  = 240;
        da_height = 270;

        xvel = 3;
        yvel = 3;
        shapesize = 20;

        verbosity            = Verbosity::ERROR;
        print_writer_samples = false;
    }

    //-------------------------------------------------------------
    ~ShapeOptions()
    {
        if (topic_name)  free(topic_name);
        if (color)       free(color);
        if (partition)   free(partition);
    }

    //-------------------------------------------------------------
    void print_usage( const char *prog )
    {
        printf("%s: \n", prog);
        printf("   -d <int>        : domain id (default: 0)\n");
        printf("   -b              : BEST_EFFORT reliability\n");
        printf("   -r              : RELIABLE reliability\n");
        printf("   -k <depth>      : keep history depth (0: KEEP_ALL)\n");
        printf("   -f <interval>   : set a 'deadline' with interval (seconds)\n");
        printf("   -i <interval>   : apply 'time based filter' with interval (seconds)\n");
        printf("   -s <int>        : set ownership strength [-1: SHARED]\n");
        printf("   -t <topic_name> : set the topic name\n");
        printf("   -c <color>      : set color to publish (filter if subscriber)\n");
        printf("   -p <partition>  : set a 'partition' string\n");
        printf("   -D [v|l|t|p]    : set durability [v: VOLATILE,  l: TRANSIENT_LOCAL]\n");
        printf("                                     t: TRANSIENT, p: PERSISTENT]\n");
        printf("   -P              : publish samples\n");
        printf("   -S              : subscribe samples\n");
        printf("   -x [1|2]        : set data representation [1: XCDR, 2: XCDR2]\n");
        printf("   -w              : print Publisher's samples\n");
        printf("   -z <int>        : set shapesize (between 10-99)\n");
        printf("   -v [e|d]        : set log message verbosity [e: ERROR, d: DEBUG]\n");
    }

    //-------------------------------------------------------------
    bool validate() {
        if (topic_name == NULL) {
            log_message("please specify topic name [-t]", Verbosity::ERROR);
            return false;
        }
        if ( (!publish) && (!subscribe) ) {
            log_message("please specify publish [-P] or subscribe [-S]", Verbosity::ERROR);
            return false;
        }
        if ( publish && subscribe ) {
            log_message("please specify only one of: publish [-P] or subscribe [-S]", Verbosity::ERROR);
            return false;
        }
        if (publish && (color == NULL) ) {
            color = strdup("BLUE");
            log_message("warning: color was not specified, defaulting to \"BLUE\"", Verbosity::ERROR);
        }
        return true;
    }

    //-------------------------------------------------------------
    bool parse(int argc, char *argv[])
    {
        int opt;
        bool parse_ok = true;
        // double d;
        while ((opt = getopt(argc, argv, "hbrc:d:D:f:i:k:p:s:x:t:v:z:wPS")) != -1)
        {
            switch (opt)
            {
            case 'v':
                {
                    if (optarg[0] != '\0')
                    {
                        switch (optarg[0])
                        {
                        case 'd':
                            {
                                verbosity = Verbosity::DEBUG;
                                break;
                            }
                        case 'e':
                            {
                                verbosity = Verbosity::ERROR;
                                break;
                            }
                        default:
                            {
                                log_message("unrecognized value for verbosity "
                                                + std::string(1, optarg[0]),
                                        Verbosity::ERROR);
                                parse_ok = false;
                            }
                        }
                    }
                    break;
                }
            case 'w':
                {
                    print_writer_samples = true;
                    break;
                }
            case 'b':
                {
                    reliability_kind = BEST_EFFORT_RELIABILITY_QOS;
                    break;
                }
            case 'c':
                {
                    color = strdup(optarg);
                    break;
                }
            case 'd':
                {
                    int converted_param = sscanf(optarg, "%d", &domain_id);
                    if (converted_param == 0) {
                        log_message("unrecognized value for domain_id "
                                        + std::string(1, optarg[0]),
                                Verbosity::ERROR);
                        parse_ok = false;
                    }
                    else if (domain_id < 0) {
                        log_message("incorrect value for domain_id "
                                        + std::to_string(domain_id),
                                Verbosity::ERROR);
                        parse_ok = false;
                    }
                    break;
                }
            case 'D':
                {
                if (optarg[0] != '\0')
                {
                    switch (optarg[0])
                    {
                    case 'v':
                        {
                            durability_kind = VOLATILE_DURABILITY_QOS;
                            break;
                        }
                    case 'l':
                        {
                            durability_kind = TRANSIENT_LOCAL_DURABILITY_QOS;
                            break;
                        }
                    case 't':
                        {
                            durability_kind = TRANSIENT_DURABILITY_QOS;
                            break;
                        }
                    case 'p':
                        {
                            durability_kind = PERSISTENT_DURABILITY_QOS;
                            break;
                        }
                    default:
                        {
                            log_message("unrecognized value for durability "
                                            + std::string(1, optarg[0]),
                                    Verbosity::ERROR);
                            parse_ok = false;
                        }
                    }
                }
                break;
                }
            case 'i':
                {
                    int converted_param = sscanf(optarg, "%d", &timebasedfilter_interval);
                    if (converted_param == 0) {
                        log_message("unrecognized value for timebasedfilter_interval "
                                        + std::string(1, optarg[0]),
                                Verbosity::ERROR);
                        parse_ok = false;
                    }
                    else if (timebasedfilter_interval < 0) {
                        log_message("incorrect value for timebasedfilter_interval "
                                        + std::to_string(timebasedfilter_interval),
                                Verbosity::ERROR);
                        parse_ok = false;
                    }
                    break;
                }
            case 'f':
                {
                    int converted_param = sscanf(optarg, "%d", &deadline_interval);
                    if (converted_param == 0) {
                        log_message("unrecognized value for deadline_interval "
                                        + std::string(1, optarg[0]),
                                Verbosity::ERROR);
                        parse_ok = false;
                    }
                    else if (deadline_interval < 0) {
                        log_message("incorrect value for deadline_interval "
                                        + std::to_string(deadline_interval),
                                Verbosity::ERROR);
                        parse_ok = false;
                    }
                    break;
                }
            case 'k':
                {
                    int converted_param = sscanf(optarg, "%d", &history_depth);
                    if (converted_param == 0){
                        log_message("unrecognized value for history_depth "
                                        + std::string(1, optarg[0]),
                                Verbosity::ERROR);
                        parse_ok = false;
                    }
                    else if (history_depth < 0) {
                        log_message("incorrect value for history_depth "
                                        + std::to_string(history_depth),
                                Verbosity::ERROR);
                        parse_ok = false;
                    }
                    break;
                }
            case 'p':
                {
                    partition = strdup(optarg);
                    break;
                }
            case 'r':
                {
                    reliability_kind = RELIABLE_RELIABILITY_QOS;
                    break;
                }
            case 's':
                {
                    int converted_param = sscanf(optarg, "%d", &ownership_strength);
                    if (converted_param == 0){
                        log_message("unrecognized value for ownership_strength "
                                        + std::string(1, optarg[0]),
                                Verbosity::ERROR);
                        parse_ok = false;
                    }
                    else if (ownership_strength < -1) {
                        log_message("incorrect value for ownership_strength "
                                        + std::to_string(ownership_strength),
                                Verbosity::ERROR);
                        parse_ok = false;
                    }
                    break;
                }
            case 't':
                {
                    topic_name = strdup(optarg);
                    break;
                }
            case 'P':
                {
                    publish = true;
                    break;
                }
            case 'S':
                {
                    subscribe = true;
                    break;
                }
            case 'h':
                {
                    print_usage(argv[0]);
                    exit(0);
                    break;
                }
            case 'x':
                {
                    if (optarg[0] != '\0')
                    {
                        switch (optarg[0])
                        {
                        case '1':
                            {
                                data_representation = XCDR_DATA_REPRESENTATION;
                                break;
                            }
                        case '2':
                            {
                                data_representation = XCDR2_DATA_REPRESENTATION;
                                break;
                            }
                        default:
                            {
                            log_message("unrecognized value for data representation "
                                            + std::string(1, optarg[0]),
                                    Verbosity::ERROR);
                            parse_ok = false;
                            }
                        }
                    }
                    break;
                }
            case 'z':
                {
                    int converted_param = sscanf(optarg, "%d", &shapesize);
                    if (converted_param == 0){
                        log_message("unrecognized value for shapesize "
                                        + std::string(1, optarg[0]),
                                Verbosity::ERROR);
                        parse_ok = false;
                    }
                    else if (shapesize < 10 || shapesize > 99) {
                        log_message("incorrect value for shapesize "
                                        + std::to_string(shapesize),
                                Verbosity::ERROR);
                        parse_ok = false;
                    }
                    break;
                }
            case '?':
                {
                    parse_ok = false;
                    break;
                }
            }

        }

        if ( parse_ok ) {
            parse_ok = validate();
        }
        if ( !parse_ok ) {
            print_usage(argv[0]);
        }
        log_message("Shape Options: "
                "\n    DomainId = " + std::to_string(domain_id) +
                "\n    ReliabilityKind = " + std::to_string(reliability_kind) +
                "\n    DurabilityKind = " + std::to_string(durability_kind) +
                "\n    DataRepresentation = " + std::to_string(data_representation) +
                "\n    HistoryDepth = " + std::to_string(history_depth) +
                "\n    OwnershipStrength = " + std::to_string(ownership_strength) +
                "\n    Publish = " + std::to_string(publish) +
                "\n    Subscribe = " + std::to_string(subscribe) +
                "\n    TimeBasedFilterInterval = " + std::to_string(timebasedfilter_interval) +
                "\n    DeadlineInterval = " + std::to_string(deadline_interval) +
                "\n    Shapesize = " + std::to_string(shapesize) +
                "\n    Verbosity = " + std::to_string(verbosity),
                Verbosity::DEBUG);
        if (topic_name != NULL){
            log_message("    Topic = " + std::string(topic_name),
                    Verbosity::DEBUG);
        }
        if (color != NULL) {
            log_message("    Color = " + std::string(color),
                    Verbosity::DEBUG);
        }
        if (partition != NULL) {
            log_message("    Partition = " + std::string(partition), Verbosity::DEBUG);
        }
        return parse_ok;
    }



    void log_message(std::string message, Verbosity level_verbosity)
    {
        if (level_verbosity <= verbosity) {
            std::cout << message << std::endl;
        }
    }

};



/*************************************************************/
class DPListener : public DomainParticipantListener
{
public:
    void on_inconsistent_topic         (Topic *topic,  const InconsistentTopicStatus &) {
        const char *topic_name = topic->get_name();
        const char *type_name  = topic->get_type_name();
        printf("%s() topic: '%s'  type: '%s'\n", __FUNCTION__, topic_name, type_name);
    }

    void on_offered_incompatible_qos(DataWriter *dw,  const OfferedIncompatibleQosStatus & status) {
        Topic      *topic       = dw->get_topic( );
        const char *topic_name  = topic->get_name( );
        const char *type_name   = topic->get_type_name( );
        const char *policy_name = NULL;
        policy_name = get_qos_policy_name(status.last_policy_id);
        printf("%s() topic: '%s'  type: '%s' : %d (%s)\n", __FUNCTION__,
                topic_name, type_name,
                status.last_policy_id,
                policy_name );
    }

    void on_publication_matched (DataWriter *dw, const PublicationMatchedStatus & status) {
        Topic      *topic      = dw->get_topic( );
        const char *topic_name = topic->get_name( );
        const char *type_name  = topic->get_type_name( );
        printf("%s() topic: '%s'  type: '%s' : matched readers %d (change = %d)\n", __FUNCTION__,
                topic_name, type_name, status.current_count, status.current_count_change);
    }

    void on_offered_deadline_missed (DataWriter *dw, const OfferedDeadlineMissedStatus & status) {
        Topic      *topic      = dw->get_topic( );
        const char *topic_name = topic->get_name( );
        const char *type_name  = topic->get_type_name( );
        printf("%s() topic: '%s'  type: '%s' : (total = %d, change = %d)\n", __FUNCTION__,
                topic_name, type_name, status.total_count, status.total_count_change);
    }

    void on_liveliness_lost (DataWriter *dw, const LivelinessLostStatus & status) {
        Topic      *topic      = dw->get_topic( );
        const char *topic_name = topic->get_name( );
        const char *type_name  = topic->get_type_name( );
        printf("%s() topic: '%s'  type: '%s' : (total = %d, change = %d)\n", __FUNCTION__,
                topic_name, type_name, status.total_count, status.total_count_change);
    }

    void on_requested_incompatible_qos (DataReader *dr, const RequestedIncompatibleQosStatus & status) {
        TopicDescription *td         = dr->get_topicdescription( );
        const char       *topic_name = td->get_name( );
        const char       *type_name  = td->get_type_name( );
        const char *policy_name = NULL;
        policy_name = get_qos_policy_name(status.last_policy_id);
        printf("%s() topic: '%s'  type: '%s' : %d (%s)\n", __FUNCTION__,
                topic_name, type_name, status.last_policy_id,
                policy_name);
    }

    void on_subscription_matched (DataReader *dr, const SubscriptionMatchedStatus & status) {
        TopicDescription *td         = dr->get_topicdescription( );
        const char       *topic_name = td->get_name( );
        const char       *type_name  = td->get_type_name( );
        printf("%s() topic: '%s'  type: '%s' : matched writers %d (change = %d)\n", __FUNCTION__,
                topic_name, type_name, status.current_count, status.current_count_change);
    }

    void on_requested_deadline_missed (DataReader *dr, const RequestedDeadlineMissedStatus & status) {
        TopicDescription *td         = dr->get_topicdescription( );
        const char       *topic_name = td->get_name( );
        const char       *type_name  = td->get_type_name( );
        printf("%s() topic: '%s'  type: '%s' : (total = %d, change = %d)\n", __FUNCTION__,
                topic_name, type_name, status.total_count, status.total_count_change);
    }

    void on_liveliness_changed (DataReader *dr, const LivelinessChangedStatus & status) {
        TopicDescription *td         = dr->get_topicdescription( );
        const char       *topic_name = td->get_name( );
        const char       *type_name  = td->get_type_name( );
        printf("%s() topic: '%s'  type: '%s' : (alive = %d, not_alive = %d)\n", __FUNCTION__,
                topic_name, type_name, status.alive_count, status.not_alive_count);
    }

  void on_sample_rejected (DataReader *, const SampleRejectedStatus &) {}
  void on_data_available (DataReader *) {}
  void on_sample_lost (DataReader *, const SampleLostStatus &) {}
  void on_data_on_readers (Subscriber *) {}
};


/*************************************************************/
class ShapeApplication {

private:
    DPListener               dp_listener;

    DomainParticipantFactory *dpf;
    DomainParticipant        *dp;
    Publisher                *pub;
    Subscriber               *sub;
    Topic                    *topic;
    ShapeTypeDataReader      *dr;
    ShapeTypeDataWriter      *dw;

    char                     *color;

    int                        xvel;
    int                        yvel;
    int                        da_width;
    int                        da_height;

public:
    //-------------------------------------------------------------
    ShapeApplication()
    {
        dpf = NULL;
        dp  = NULL;

        pub = NULL;
        sub = NULL;
        color = NULL;
    }

    //-------------------------------------------------------------
    ~ShapeApplication()
    {
        if (dp)  dp->delete_contained_entities( );
        if (dpf) dpf->delete_participant( dp );

        if (color) free(color);
    }

    //-------------------------------------------------------------
    bool initialize(ShapeOptions *options)
    {
#ifndef OBTAIN_DOMAIN_PARTICIPANT_FACTORY
#define OBTAIN_DOMAIN_PARTICIPANT_FACTORY DomainParticipantFactory::get_instance()
#endif
        DomainParticipantFactory *dpf = OBTAIN_DOMAIN_PARTICIPANT_FACTORY;
        if (dpf == NULL) {
            options->log_message("failed to create participant factory (missing license?).", Verbosity::ERROR);
            return false;
        }
        options->log_message("Participant Factory created", Verbosity::DEBUG);
#ifdef CONFIGURE_PARTICIPANT_FACTORY
        CONFIGURE_PARTICIPANT_FACTORY
#endif

        dp = dpf->create_participant( options->domain_id, PARTICIPANT_QOS_DEFAULT, &dp_listener, LISTENER_STATUS_MASK_ALL );
        if (dp == NULL) {
            options->log_message("failed to create participant (missing license?).", Verbosity::ERROR);
            return false;
        }
        options->log_message("Participant created", Verbosity::DEBUG);
#ifndef REGISTER_TYPE
#define REGISTER_TYPE ShapeTypeTypeSupport::register_type
#endif
        REGISTER_TYPE(dp, "ShapeType");

        printf("Create topic: %s\n", options->topic_name );
        topic = dp->create_topic( options->topic_name, "ShapeType", TOPIC_QOS_DEFAULT, NULL, 0);
        if (topic == NULL) {
            options->log_message("failed to create topic", Verbosity::ERROR);
            return false;
        }

        if ( options->publish ) {
            return init_publisher(options);
        }
        else {
            return init_subscriber(options);
        }
    }

    //-------------------------------------------------------------
    bool run(ShapeOptions *options)
    {
        if ( pub != NULL ) {
            return run_publisher(options);
        }
        else if ( sub != NULL ) {
            return run_subscriber();
        }

        return false;
    }

    //-------------------------------------------------------------
    bool init_publisher(ShapeOptions *options)
    {
        options->log_message("Initializing Publisher", Verbosity::DEBUG);
        PublisherQos  pub_qos;
        DataWriterQos dw_qos;
        ShapeType     shape;

        dp->get_default_publisher_qos( pub_qos );
        if ( options->partition != NULL ) {
            StringSeq_push(pub_qos.partition.name, options->partition);
        }

        pub = dp->create_publisher(pub_qos, NULL, 0);
        if (pub == NULL) {
            options->log_message("failed to create publisher", Verbosity::ERROR);
            return false;
        }
        options->log_message("Publisher created", Verbosity::DEBUG);
        options->log_message("Data Writer QoS:", Verbosity::DEBUG);
        pub->get_default_datawriter_qos( dw_qos );
        dw_qos.reliability.kind = options->reliability_kind;
        options->log_message("    Reliability = " + std::to_string(dw_qos.reliability.kind), Verbosity::DEBUG);
        dw_qos.durability.kind  = options->durability_kind;
        options->log_message("    Durability = " + std::to_string(dw_qos.durability.kind), Verbosity::DEBUG);

#if   defined(RTI_CONNEXT_DDS)
        DataRepresentationIdSeq data_representation_seq;
        data_representation_seq.ensure_length(1,1);
        data_representation_seq[0] = options->data_representation;
        dw_qos.representation.value = data_representation_seq;

#elif   defined(OPENDDS)
        dw_qos.representation.value.length(1);
        dw_qos.representation.value[0] = options->data_representation;
#endif
        options->log_message("    Data_Representation = " + std::to_string(dw_qos.representation.value[0]), Verbosity::DEBUG);
        if ( options->ownership_strength != -1 ) {
            dw_qos.ownership.kind = EXCLUSIVE_OWNERSHIP_QOS;
            dw_qos.ownership_strength.value = options->ownership_strength;
        }

        if ( options->ownership_strength == -1 ) {
            dw_qos.ownership.kind = SHARED_OWNERSHIP_QOS;
        }
        options->log_message("    Ownership = " + std::to_string(dw_qos.ownership.kind), Verbosity::DEBUG);
        options->log_message("    OwnershipStrength = " + std::to_string(dw_qos.ownership_strength.value), Verbosity::DEBUG);

        if ( options->deadline_interval > 0 ) {
            dw_qos.deadline.period.sec      = options->deadline_interval;
            dw_qos.deadline.period.nanosec  = 0;
        }
        options->log_message("    DeadlinePeriod = " + std::to_string(dw_qos.deadline.period.sec), Verbosity::DEBUG);

        // options->history_depth < 0 means leave default value
        if ( options->history_depth > 0 )  {
            dw_qos.history.kind  = KEEP_LAST_HISTORY_QOS;
            dw_qos.history.depth = options->history_depth;
        }
        else if ( options->history_depth == 0 ) {
            dw_qos.history.kind  = KEEP_ALL_HISTORY_QOS;
        }
        options->log_message("    HistoryKind = " + std::to_string(dw_qos.history.kind), Verbosity::DEBUG);
        options->log_message("    HistoryDepth = " + std::to_string(dw_qos.history.depth), Verbosity::DEBUG);

        printf("Create writer for topic: %s color: %s\n", options->topic_name, options->color );
        dw = dynamic_cast<ShapeTypeDataWriter *>(pub->create_datawriter( topic, dw_qos, NULL, 0));

        if (dw == NULL) {
            options->log_message("failed to create datawriter", Verbosity::ERROR);
            return false;
        }

        color = strdup(options->color);
        xvel = options->xvel;
        yvel = options->yvel;
        da_width  = options->da_width;
        da_height = options->da_height;
        options->log_message("Data Writer created", Verbosity::DEBUG);
        options->log_message("Color " + std::string(color), Verbosity::DEBUG);
        options->log_message("xvel " + std::to_string(xvel), Verbosity::DEBUG);
        options->log_message("yvel " + std::to_string(yvel), Verbosity::DEBUG);
        options->log_message("da_width " + std::to_string(da_width), Verbosity::DEBUG);
        options->log_message("da_height " + std::to_string(da_height), Verbosity::DEBUG);

        return true;
    }

    //-------------------------------------------------------------
    bool init_subscriber(ShapeOptions *options)
    {
        SubscriberQos sub_qos;
        DataReaderQos dr_qos;

        dp->get_default_subscriber_qos( sub_qos );
        if ( options->partition != NULL ) {
            StringSeq_push(sub_qos.partition.name, options->partition);
        }

        sub = dp->create_subscriber( sub_qos, NULL, 0 );
        if (sub == NULL) {
            options->log_message("failed to create subscriber", Verbosity::ERROR);
            return false;
        }
        options->log_message("Subscriber created", Verbosity::DEBUG);
        options->log_message("Data Reader QoS:", Verbosity::DEBUG);
        sub->get_default_datareader_qos( dr_qos );
        dr_qos.reliability.kind = options->reliability_kind;
        options->log_message("    Reliability = " + std::to_string(dr_qos.reliability.kind), Verbosity::DEBUG);
        dr_qos.durability.kind  = options->durability_kind;
        options->log_message("    Durability = " + std::to_string(dr_qos.durability.kind), Verbosity::DEBUG);

#if   defined(RTI_CONNEXT_DDS)
            DataRepresentationIdSeq data_representation_seq;
            data_representation_seq.ensure_length(1,1);
            data_representation_seq[0] = options->data_representation;
            dr_qos.representation.value = data_representation_seq;

#elif   defined(OPENDDS)
        dr_qos.representation.value.length(1);
        dr_qos.representation.value[0] = options->data_representation;
#endif
        options->log_message("    DataRepresentation = " + std::to_string(dr_qos.representation.value[0]), Verbosity::DEBUG);
        if ( options->ownership_strength != -1 ) {
            dr_qos.ownership.kind = EXCLUSIVE_OWNERSHIP_QOS;
        }

        if ( options->timebasedfilter_interval > 0) {
            dr_qos.time_based_filter.minimum_separation.sec      = options->timebasedfilter_interval;
            dr_qos.time_based_filter.minimum_separation.nanosec  = 0;
        }
        options->log_message("    Ownership = " + std::to_string(dr_qos.ownership.kind), Verbosity::DEBUG);

        if ( options->deadline_interval > 0 ) {
            dr_qos.deadline.period.sec      = options->deadline_interval;
            dr_qos.deadline.period.nanosec  = 0;
        }
        options->log_message("    DeadlinePeriod = " + std::to_string(dr_qos.deadline.period.sec), Verbosity::DEBUG);

        // options->history_depth < 0 means leave default value
        if ( options->history_depth > 0 )  {
            dr_qos.history.kind  = KEEP_LAST_HISTORY_QOS;
            dr_qos.history.depth = options->history_depth;
        }
        else if ( options->history_depth == 0 ) {
            dr_qos.history.kind  = KEEP_ALL_HISTORY_QOS;
        }
        options->log_message("    HistoryKind = " + std::to_string(dr_qos.history.kind), Verbosity::DEBUG);
        options->log_message("    HistoryDepth = " + std::to_string(dr_qos.history.depth), Verbosity::DEBUG);

        if ( options->color != NULL ) {
            /*  filter on specified color */
            ContentFilteredTopic *cft;
            StringSeq              cf_params;

#if   defined(RTI_CONNEXT_DDS)
            char parameter[64];
            sprintf(parameter, "'%s'",  options->color);
            StringSeq_push(cf_params, parameter);
            cft = dp->create_contentfilteredtopic(options->topic_name, topic, "color MATCH %0", cf_params);
            options->log_message("    ContentFilterTopic = color MATCH " + std::string(parameter), Verbosity::DEBUG);
#elif defined(TWINOAKS_COREDX) || defined(OPENDDS)
            StringSeq_push(cf_params, options->color);
            cft = dp->create_contentfilteredtopic(options->topic_name, topic, "color = %0", cf_params);
            options->log_message("    ContentFilterTopic = color = " + std::string(options->color), Verbosity::DEBUG);
#endif
            if (cft == NULL) {
                options->log_message("failed to create content filtered topic", Verbosity::ERROR);
                return false;
            }

            printf("Create reader for topic: %s color: %s\n", options->topic_name, options->color );
            dr = dynamic_cast<ShapeTypeDataReader *>(sub->create_datareader(cft, dr_qos, NULL, 0));
        }
        else  {
            printf("Create reader for topic: %s\n", options->topic_name );
            dr = dynamic_cast<ShapeTypeDataReader *>(sub->create_datareader(topic, dr_qos, NULL, 0));
        }


        if (dr == NULL) {
            options->log_message("failed to create datareader", Verbosity::ERROR);
            return false;
        }
        options->log_message("Data Reader created", Verbosity::DEBUG);
        return true;
    }

    //-------------------------------------------------------------
    bool run_subscriber()
    {
        while ( ! all_done )  {
            ReturnCode_t     retval;
            SampleInfoSeq    sample_infos;

#if   defined(RTI_CONNEXT_DDS) || defined(OPENDDS)
            ShapeTypeSeq          samples;
#elif defined(TWINOAKS_COREDX)
            ShapeTypePtrSeq       samples;
#endif

            InstanceHandle_t previous_handle = HANDLE_NIL;

            do {
#if   defined(RTI_CONNEXT_DDS) || defined(OPENDDS)
                retval = dr->take_next_instance ( samples,
                        sample_infos,
                        LENGTH_UNLIMITED,
                        previous_handle,
                        ANY_SAMPLE_STATE,
                        ANY_VIEW_STATE,
                        ANY_INSTANCE_STATE );
#elif defined(TWINOAKS_COREDX)
                retval = dr->take_next_instance ( &samples,
                        &sample_infos,
                        LENGTH_UNLIMITED,
                        previous_handle,
                        ANY_SAMPLE_STATE,
                        ANY_VIEW_STATE,
                        ANY_INSTANCE_STATE );
#endif

                if (retval == RETCODE_OK) {
                    int i;
                    for (i = 0; i < samples.length(); i++)  {

#if   defined(RTI_CONNEXT_DDS) || defined(OPENDDS)
                        ShapeType          *sample      = &samples[i];
                        SampleInfo         *sample_info = &sample_infos[i];
#elif defined(TWINOAKS_COREDX)
                        ShapeType          *sample      = samples[i];
                        SampleInfo         *sample_info = sample_infos[i];
#endif

                        if (sample_info->valid_data)  {
                            printf("%-10s %-10s %03d %03d [%d]\n", dr->get_topicdescription()->get_name(),
                                    sample->color STRING_IN,
                                    sample->x,
                                    sample->y,
                                    sample->shapesize );
                        }
                    }

#if   defined(RTI_CONNEXT_DDS) || defined(OPENDDS)
                    previous_handle = sample_infos[0].instance_handle;
                    dr->return_loan( samples, sample_infos );
#elif defined(TWINOAKS_COREDX)
                    previous_handle = sample_infos[0]->instance_handle;
                    dr->return_loan( &samples, &sample_infos );
#endif
                }
            } while (retval == RETCODE_OK);

            usleep(100000);
        }

        return true;
    }

    //-------------------------------------------------------------
    void
    moveShape( ShapeType *shape)
    {
        int w2;

        w2 = 1 + shape->shapesize / 2;
        shape->x = shape->x + xvel;
        shape->y = shape->y + yvel;
        if (shape->x < w2) {
            shape->x = w2;
            xvel = -xvel;
        }
        if (shape->x > da_width - w2) {
            shape->x = (da_width - w2);
            xvel = -xvel;
        }
        if (shape->y < w2) {
            shape->y = w2;
            yvel = -yvel;
        }
        if (shape->y > (da_height - w2) )  {
            shape->y = (da_height - w2);
            yvel = -yvel;
        }
    }

    //-------------------------------------------------------------
    bool run_publisher(ShapeOptions *options)
    {
        ShapeType shape;
#if defined(RTI_CONNEXT_DDS)
        ShapeType_initialize(&shape);
#endif

        srandom((uint32_t)time(NULL));

#ifndef STRING_ALLOC
#define STRING_ALLOC(A, B)
#endif
        STRING_ALLOC(shape.color, std::strlen(color));
        strcpy(shape.color STRING_INOUT, color);

        shape.shapesize = options->shapesize;
        shape.x    =  random() % da_width;
        shape.y    =  random() % da_height;
        xvel       =  ((random() % 5) + 1) * ((random()%2)?-1:1);
        yvel       =  ((random() % 5) + 1) * ((random()%2)?-1:1);;

        while ( ! all_done )  {
            moveShape(&shape);
#if   defined(RTI_CONNEXT_DDS) || defined(OPENDDS)
            dw->write( shape, HANDLE_NIL );
#elif defined(TWINOAKS_COREDX)
            dw->write( &shape, HANDLE_NIL );
#endif
            if (options->print_writer_samples)
                printf("%-10s %-10s %03d %03d [%d]\n", dw->get_topic()->get_name(),
                                        shape.color STRING_IN,
                                        shape.x,
                                        shape.y,
                                        shape.shapesize);
            usleep(33000);
        }

        return true;
    }
};

/*************************************************************/
int main( int argc, char * argv[] )
{
    install_sig_handlers();

    ShapeOptions options;
    bool parseResult = options.parse(argc, argv);
    if ( !parseResult  ) {
        exit(1);
    }
    ShapeApplication shapeApp;
    if ( !shapeApp.initialize(&options) ) {
        exit(2);
    }
    if ( !shapeApp.run(&options) ) {
        exit(2);
    }

    printf("Done.\n");

    return 0;
}
