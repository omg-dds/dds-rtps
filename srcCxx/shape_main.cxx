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


/*************************************************************/
class ShapeOptions {
public:
    DomainId_t                     domain_id;
    ReliabilityQosPolicyKind       reliability_kind;
    DurabilityQosPolicyKind        durability_kind;
    int                            history_depth;
    int                            ownership_strength;

    char              * topic_name;
    char              * color;
    char              * partition;

    bool                publish;
    bool                subscribe;

    int                 timebasedfilter_interval;
    int                 deadline_interval;

    int                 da_width;
    int                 da_height;

    int                 xvel;
    int                 yvel;

public:
    //-------------------------------------------------------------
    ShapeOptions()
    {
        domain_id           = 0;
        reliability_kind    = RELIABLE_RELIABILITY_QOS;
        durability_kind     = VOLATILE_DURABILITY_QOS;
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
    }

    //-------------------------------------------------------------
    ~ShapeOptions()
    {
        if (topic_name)  free(topic_name);
        if (color)       free(color);
        if (partition)   free(partition);
    }

    //-------------------------------------------------------------
    void print_usage( const char * prog )
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
    }

    //-------------------------------------------------------------
    bool validate() {
        if (topic_name == NULL) {
            printf("please specify topic name [-t]\n");
            return false;
        }
        if ( (!publish) && (!subscribe) ) {
            printf("please specify publish [-P] or subscribe [-S]\n");
            return false;
        }
        if ( publish && subscribe ) {
            printf("please specify only one of: publish [-P] or subscribe [-S]\n");
            return false;
        }
        if (publish && (color == NULL) ) {
            color = strdup("BLUE");
            printf("warning: color was not specified, defaulting to \"BLUE\"\n");
        }
        return true;
    }

    //-------------------------------------------------------------
    bool parse(int argc, char * argv[])
    {
        int opt;
        bool parse_ok = true;

        // double d;
        while ((opt = getopt(argc, argv, "hbrc:d:D:f:i:k:p:s:t:PS")) != -1)
        {
            switch (opt)
            {
            case 'b':
                reliability_kind = BEST_EFFORT_RELIABILITY_QOS;
                break;
            case 'c':
                color = strdup(optarg);
                break;
            case 'd':
                domain_id = atoi(optarg);
                break;
            case 'D':
                if (optarg[0] != '\0')
                {
                    switch (optarg[0])
                    {
                    case 'v':
                        durability_kind = VOLATILE_DURABILITY_QOS;
                        break;
                    case 'l':
                        durability_kind = TRANSIENT_LOCAL_DURABILITY_QOS;
                        break;
                    case 't':
                        durability_kind = TRANSIENT_DURABILITY_QOS;
                        break;
                    case 'p':
                        durability_kind = PERSISTENT_DURABILITY_QOS;
                        break;
                    default:
                        printf("unrecognized value for durability '%c'\n", optarg[0]);
                        parse_ok = false;
                    }
                }
                break;
            case 'i':
                timebasedfilter_interval = atoi(optarg);
                break;
            case 'f':
                deadline_interval = atoi(optarg);
                break;
            case 'k':
                history_depth = atoi(optarg);
                if (history_depth <= 0) {
                    printf("unrecognized value for history_depth '%c'\n", optarg[0]);
                    parse_ok = false;
                }
                break;
            case 'p':
                partition = strdup(optarg);
                break;
            case 'r':
                reliability_kind = RELIABLE_RELIABILITY_QOS;
                break;
            case 's':
                ownership_strength = atoi(optarg);
                if (ownership_strength <= 0) {
                    printf("unrecognized value for ownership_strength '%c'\n", optarg[0]);
                    parse_ok = false;
                }
                break;
            case 't':
                topic_name = strdup(optarg);
                break;
            case 'P':
                publish = true;
                break;
            case 'S':
                subscribe = true;
                break;

            case 'h':
                print_usage(argv[0]);
                exit(0);
                break;

            case '?':
                parse_ok = false;
                break;
            }

        }

        if ( parse_ok ) {
            parse_ok = validate();
        }
        if ( !parse_ok ) {
            print_usage(argv[0]);
        }
        return parse_ok;
    }
};



/*************************************************************/
class DPListener : public DomainParticipantListener
{
public:
    void on_inconsistent_topic         ( Topic * topic,  const InconsistentTopicStatus &) {
        const char * topic_name = topic->get_name();
        const char * type_name  = topic->get_type_name();
        printf("%s() topic: '%s'  type: '%s'\n", __FUNCTION__, topic_name, type_name);
    }

    void on_offered_incompatible_qos( DataWriter *dw,  const OfferedIncompatibleQosStatus & status ) {
        Topic      * topic       = dw->get_topic( );
        const char * topic_name  = topic->get_name( );
        const char * type_name   = topic->get_type_name( );
        const char * policy_name = NULL;
        policy_name = get_qos_policy_name(status.last_policy_id);
        printf("%s() topic: '%s'  type: '%s' : %d (%s)\n", __FUNCTION__,
                topic_name, type_name,
                status.last_policy_id,
                policy_name );
    }

    void on_publication_matched (DataWriter * dw, const PublicationMatchedStatus & status) {
        Topic      * topic      = dw->get_topic( );
        const char * topic_name = topic->get_name( );
        const char * type_name  = topic->get_type_name( );
        printf("%s() topic: '%s'  type: '%s' : matched readers %d (change = %d)\n", __FUNCTION__,
                topic_name, type_name, status.current_count, status.current_count_change);
    }

    void on_offered_deadline_missed (DataWriter * dw, const OfferedDeadlineMissedStatus & status) {
        Topic      * topic      = dw->get_topic( );
        const char * topic_name = topic->get_name( );
        const char * type_name  = topic->get_type_name( );
        printf("%s() topic: '%s'  type: '%s' : (total = %d, change = %d)\n", __FUNCTION__,
                topic_name, type_name, status.total_count, status.total_count_change);
    }

    void on_liveliness_lost (DataWriter * dw, const LivelinessLostStatus & status) {
        Topic      * topic      = dw->get_topic( );
        const char * topic_name = topic->get_name( );
        const char * type_name  = topic->get_type_name( );
        printf("%s() topic: '%s'  type: '%s' : (total = %d, change = %d)\n", __FUNCTION__,
                topic_name, type_name, status.total_count, status.total_count_change);
    }

    void on_requested_incompatible_qos ( DataReader * dr, const RequestedIncompatibleQosStatus & status ) {
        TopicDescription * td         = dr->get_topicdescription( );
        const char       * topic_name = td->get_name( );
        const char       * type_name  = td->get_type_name( );
        const char * policy_name = NULL;
        policy_name = get_qos_policy_name(status.last_policy_id);
        printf("%s() topic: '%s'  type: '%s' : %d (%s)\n", __FUNCTION__,
                topic_name, type_name, status.last_policy_id,
                policy_name);
    }

    void on_subscription_matched (DataReader * dr, const SubscriptionMatchedStatus & status) {
        TopicDescription * td         = dr->get_topicdescription( );
        const char       * topic_name = td->get_name( );
        const char       * type_name  = td->get_type_name( );
        printf("%s() topic: '%s'  type: '%s' : matched writers %d (change = %d)\n", __FUNCTION__,
                topic_name, type_name, status.current_count, status.current_count_change);
    }

    void on_requested_deadline_missed (DataReader * dr, const RequestedDeadlineMissedStatus & status) {
        TopicDescription * td         = dr->get_topicdescription( );
        const char       * topic_name = td->get_name( );
        const char       * type_name  = td->get_type_name( );
        printf("%s() topic: '%s'  type: '%s' : (total = %d, change = %d)\n", __FUNCTION__,
                topic_name, type_name, status.total_count, status.total_count_change);
    }

    void on_liveliness_changed (DataReader * dr, const LivelinessChangedStatus & status) {
        TopicDescription * td         = dr->get_topicdescription( );
        const char       * topic_name = td->get_name( );
        const char       * type_name  = td->get_type_name( );
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

    DomainParticipantFactory * dpf;
    DomainParticipant        * dp;
    Publisher                * pub;
    Subscriber               * sub;
    Topic                    * topic;
    ShapeTypeDataReader      * dr;
    ShapeTypeDataWriter      * dw;

    char                     * color;

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
            printf("failed to create participant factory (missing license?).\n");
            return false;
        }

#ifdef CONFIGURE_PARTICIPANT_FACTORY
        CONFIGURE_PARTICIPANT_FACTORY
#endif

        dp = dpf->create_participant( options->domain_id, PARTICIPANT_QOS_DEFAULT, &dp_listener, LISTENER_STATUS_MASK_ALL );
        if (dp == NULL) {
            printf("failed to create participant (missing license?).\n");
            return false;
        }

#ifndef REGISTER_TYPE
#define REGISTER_TYPE ShapeTypeTypeSupport::register_type
#endif
        REGISTER_TYPE(dp, "ShapeType");

        printf("Create topic: %s\n", options->topic_name );
        topic = dp->create_topic( options->topic_name, "ShapeType", TOPIC_QOS_DEFAULT, NULL, 0);
        if (topic == NULL) {
            printf("failed to create topic\n");
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
    bool run()
    {
        if ( pub != NULL ) {
            return run_publisher();
        }
        else if ( sub != NULL ) {
            return run_subscriber();
        }

        return false;
    }

    //-------------------------------------------------------------
    bool init_publisher(ShapeOptions *options)
    {

        PublisherQos  pub_qos;
        DataWriterQos dw_qos;
        ShapeType     shape;

        dp->get_default_publisher_qos( pub_qos );
        if ( options->partition != NULL ) {
            StringSeq_push(pub_qos.partition.name, options->partition);
        }

        pub = dp->create_publisher(pub_qos, NULL, 0);
        if (pub == NULL) {
            printf("failed to create publisher");
            return false;
        }

        pub->get_default_datawriter_qos( dw_qos );
        dw_qos.reliability.kind = options->reliability_kind;
        dw_qos.durability.kind  = options->durability_kind;

        if ( options->ownership_strength != -1 ) {
            dw_qos.ownership.kind = EXCLUSIVE_OWNERSHIP_QOS;
            dw_qos.ownership_strength.value = options->ownership_strength;
        }

        if ( options->deadline_interval > 0 ) {
            dw_qos.deadline.period.sec      = options->deadline_interval;
            dw_qos.deadline.period.nanosec  = 0;
        }

        // options->history_depth < 0 means leave default value
        if ( options->history_depth > 0 )  {
            dw_qos.history.kind  = KEEP_LAST_HISTORY_QOS;
            dw_qos.history.depth = options->history_depth;
        }
        else if ( options->history_depth == 0 ) {
            dw_qos.history.kind  = KEEP_ALL_HISTORY_QOS;
        }

        printf("Create writer for topic: %s color: %s\n", options->topic_name, options->color );
        dw = dynamic_cast<ShapeTypeDataWriter *>(pub->create_datawriter( topic, dw_qos, NULL, 0));

        if (dw == NULL) {
            printf("failed to create datawriter");
            return false;
        }

        color = strdup(options->color);
        xvel = options->xvel;
        yvel = options->yvel;
        da_width  = options->da_width;
        da_height = options->da_height;

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
            printf("failed to create subscriber");
            return false;
        }

        sub->get_default_datareader_qos( dr_qos );
        dr_qos.reliability.kind = options->reliability_kind;
        dr_qos.durability.kind  = options->durability_kind;

        if ( options->ownership_strength != -1 ) {
            dr_qos.ownership.kind = EXCLUSIVE_OWNERSHIP_QOS;
        }

        if ( options->timebasedfilter_interval > 0) {
            dr_qos.time_based_filter.minimum_separation.sec      = options->timebasedfilter_interval;
            dr_qos.time_based_filter.minimum_separation.nanosec  = 0;
        }

        if ( options->deadline_interval > 0 ) {
            dr_qos.deadline.period.sec      = options->deadline_interval;
            dr_qos.deadline.period.nanosec  = 0;
        }

        // options->history_depth < 0 means leave default value
        if ( options->history_depth > 0 )  {
            dr_qos.history.kind  = KEEP_LAST_HISTORY_QOS;
            dr_qos.history.depth = options->history_depth;
        }
        else if ( options->history_depth == 0 ) {
            dr_qos.history.kind  = KEEP_ALL_HISTORY_QOS;
        }

        if ( options->color != NULL ) {
            /*  filter on specified color */
            ContentFilteredTopic * cft;
            StringSeq              cf_params;

#if   defined(RTI_CONNEXT_DDS)
            char paramater[64];
            sprintf(paramater, "'%s'",  options->color);
            StringSeq_push(cf_params, paramater);
            cft = dp->create_contentfilteredtopic( options->topic_name, topic, "color MATCH %0", cf_params );
#elif defined(TWINOAKS_COREDX) || defined(OPENDDS)
            StringSeq_push(cf_params, options->color);
            cft = dp->create_contentfilteredtopic( options->topic_name, topic, "color = %0", cf_params );
#endif
            if (cft == NULL) {
                printf("failed to create content filtered topic");
                return false;
            }

            printf("Create reader for topic: %s color: %s\n", options->topic_name, options->color );
            dr = dynamic_cast<ShapeTypeDataReader *>(sub->create_datareader( cft, dr_qos, NULL, 0));
        }
        else  {
            printf("Create reader for topic: %s\n", options->topic_name );
            dr = dynamic_cast<ShapeTypeDataReader *>(sub->create_datareader( topic, dr_qos, NULL, 0));
        }

        if (dr == NULL) {
            printf("failed to create datareader");
            return false;
        }

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
                    for (i = samples.length()-1; i>=0; i--)  {

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
                            break;
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
    moveShape( ShapeType * shape)
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
    bool run_publisher()
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

        shape.shapesize = 20;
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

    if ( !shapeApp.run() ) {
        exit(2);
    }

    printf("Done.\n");

    return 0;
}
