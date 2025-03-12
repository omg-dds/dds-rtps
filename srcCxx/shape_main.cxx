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
#include <getopt.h>
#include <sys/types.h>

#if defined(RTI_CONNEXT_DDS)
#include "shape_configurator_rti_connext_dds.h"
#elif defined(TWINOAKS_COREDX)
#include "shape_configurator_toc_coredx_dds.h"
#elif defined(OPENDDS)
#include "shape_configurator_opendds.h"
#elif defined(EPROSIMA_FAST_DDS)
#include "shape_configurator_eprosima_fast_dds.h"
#elif defined(INTERCOM_DDS)
#include "shape_configurator_intercom_dds.h"
#else
#error "Must define the DDS vendor"
#endif

#ifndef STRING_IN
#define STRING_IN
#endif
#ifndef STRING_INOUT
#define STRING_INOUT
#endif
#ifndef NAME_ACCESSOR
#define NAME_ACCESSOR
#endif
#ifndef LISTENER_STATUS_MASK_NONE
#define LISTENER_STATUS_MASK_NONE 0
#endif
#ifndef SECONDS_FIELD_NAME
#define SECONDS_FIELD_NAME sec
#endif
#ifndef FIELD_ACCESSOR
#define FIELD_ACCESSOR
#endif
#ifndef GET_TOPIC_DESCRIPTION
#define GET_TOPIC_DESCRIPTION(dr) dr->get_topicdescription()
#endif
#ifndef ADD_PARTITION
#define ADD_PARTITION(field, value) StringSeq_push(field.name, value)
#endif

using namespace DDS;

#define ERROR_PARSING_ARGUMENTS 1
#define ERROR_INITIALIZING 2
#define ERROR_RUNNING 3

#ifndef STRING_FREE
#define STRING_FREE free
#endif

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

class QosUtils {
public:
    static std::string to_string(ReliabilityQosPolicyKind reliability_value)
    {
        if (reliability_value == BEST_EFFORT_RELIABILITY_QOS){
            return "BEST_EFFORT";
        } else if (reliability_value == RELIABLE_RELIABILITY_QOS){
            return "RELIABLE";
        }
        return "Error stringifying Reliability kind.";
    }

    static std::string to_string(DurabilityQosPolicyKind durability_value)
    {
        if ( durability_value == VOLATILE_DURABILITY_QOS){
            return "VOLATILE";
        } else if (durability_value == TRANSIENT_LOCAL_DURABILITY_QOS){
            return "TRANSIENT_LOCAL";
        } else if (durability_value == TRANSIENT_DURABILITY_QOS){
            return "TRANSIENT";
        } else if (durability_value == PERSISTENT_DURABILITY_QOS){
            return "PERSISTENT";
        }
        return "Error stringifying Durability kind.";
    }

    static std::string to_string(DataRepresentationId_t data_representation_value)
    {
        if (data_representation_value == XCDR_DATA_REPRESENTATION){
            return "XCDR";
        } else if (data_representation_value == XCDR2_DATA_REPRESENTATION){
            return "XCDR2";
        }
        return "Error stringifying DataRepresentation.";
    }

    static std::string to_string(Verbosity verbosity_value)
    {
        switch (verbosity_value)
        {
        case ERROR:
            return "ERROR";
            break;

        case DEBUG:
            return "DEBUG";
            break;

        default:
            break;
        }
        return "Error stringifying verbosity.";
    }

    static std::string to_string(OwnershipQosPolicyKind ownership_kind_value)
    {
        if (ownership_kind_value == SHARED_OWNERSHIP_QOS){
            return "SHARED";
        } else if (ownership_kind_value == EXCLUSIVE_OWNERSHIP_QOS){
            return "EXCLUSIVE";
        }
        return "Error stringifying Ownership kind.";
    }

    static std::string to_string(HistoryQosPolicyKind history_kind_value)
    {
        if (history_kind_value == KEEP_ALL_HISTORY_QOS){
            return "KEEP_ALL";
        } else if (history_kind_value == KEEP_LAST_HISTORY_QOS){
            return "KEEP_LAST";
        }
        return "Error stringifying History kind.";
    }

    static std::string to_string(PresentationQosPolicyAccessScopeKind access_scope)
    {
        if (access_scope == INSTANCE_PRESENTATION_QOS) {
            return "INSTANCE_PRESENTATION_QOS";
        } else if (access_scope == TOPIC_PRESENTATION_QOS) {
            return "TOPIC_PRESENTATION_QOS";
        } else if (access_scope == GROUP_PRESENTATION_QOS) {
            return "GROUP_PRESENTATION_QOS";
        }
        return "Error stringifying Access Scope kind.";
    }
};

class Logger{
public:
    Logger(enum Verbosity v)
    {
        verbosity_ = v;
    }

    void verbosity(enum Verbosity v)
    {
        verbosity_ = v;
    }

    enum Verbosity verbosity()
    {
        return verbosity_;
    }

    void log_message(std::string message, enum Verbosity level_verbosity)
    {
        if (level_verbosity <= verbosity_) {
            std::cout << message << std::endl;
        }
    }

private:
    enum Verbosity verbosity_;
};

/*************************************************************/
Logger logger(ERROR);
/*************************************************************/
class ShapeOptions {
public:
    DomainId_t                             domain_id;
    ReliabilityQosPolicyKind               reliability_kind;
    DurabilityQosPolicyKind                durability_kind;
    DataRepresentationId_t                 data_representation;
    int                                    history_depth;
    int                                    ownership_strength;
    PresentationQosPolicyAccessScopeKind   coherent_set_access_scope;


    char               *topic_name;
    char               *color;
    char               *partition;

    bool                publish;
    bool                subscribe;

    int                 timebasedfilter_interval;
    int                 deadline_interval;
    useconds_t          lifespan_us;

    int                 da_width;
    int                 da_height;

    int                 xvel;
    int                 yvel;
    int                 shapesize;

    bool                print_writer_samples;

    bool                use_read;

    useconds_t          write_period_us;
    useconds_t          read_period_us;
    unsigned int        num_iterations;

    unsigned int        num_instances;
    unsigned int        num_topics;

    bool                unregister;
    bool                dispose;

    bool                coherent_set_access_scope_set;
    bool                coherent_set_enabled;
    bool                ordered_access_enabled;
    unsigned int        coherent_set_sample_count;

    unsigned int        additional_payload_size;

    bool                take_read_next_instance;

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
        lifespan_us              = 0; /* off */

        da_width  = 240;
        da_height = 270;

        xvel = 3;
        yvel = 3;
        shapesize = 20;

        print_writer_samples = false;

        use_read = false;

        write_period_us = 33000;
        read_period_us = 100000;

        num_iterations = 0;
        num_instances = 1;
        num_topics = 1;

        unregister = false;
        dispose = false;

        coherent_set_enabled = false;
        ordered_access_enabled = false;
        coherent_set_access_scope_set = false;
        coherent_set_access_scope = INSTANCE_PRESENTATION_QOS;
        coherent_set_sample_count = 0;

        additional_payload_size = 0;

        take_read_next_instance = true;
    }

    //-------------------------------------------------------------
    ~ShapeOptions()
    {
        STRING_FREE(topic_name);
        STRING_FREE(color);
        STRING_FREE(partition);
    }

    //-------------------------------------------------------------
    void print_usage( const char *prog )
    {
        printf("%s: \n", prog);
        printf("   --help, -h      : print this menu\n");
        printf("   -v [e|d]        : set log message verbosity [e: ERROR, d: DEBUG]\n");
        printf("   -P              : publish samples\n");
        printf("   -S              : subscribe samples\n");
        printf("   -d <int>        : domain id (default: 0)\n");
        printf("   -b              : BEST_EFFORT reliability\n");
        printf("   -r              : RELIABLE reliability\n");
        printf("   -k <depth>      : keep history depth [0: KEEP_ALL]\n");
        printf("   -f <interval>   : set a 'deadline' with interval (seconds) [0: OFF]\n");
        printf("   -i <interval>   : apply 'time based filter' with interval (seconds) [0: OFF]\n");
        printf("   -s <strength>   : set ownership strength [-1: SHARED]\n");
        printf("   -t <topic_name> : set the topic name\n");
        printf("   -c <color>      : set color to publish (filter if subscriber)\n");
        printf("   -p <partition>  : set a 'partition' string\n");
        printf("   -D [v|l|t|p]    : set durability [v: VOLATILE,  l: TRANSIENT_LOCAL]\n");
        printf("                                     t: TRANSIENT, p: PERSISTENT]\n");
        printf("   -x [1|2]        : set data representation [1: XCDR, 2: XCDR2]\n");
        printf("   -w              : print Publisher's samples\n");
        printf("   -z <int>        : set shapesize (0: increase the size for every sample)\n");
        printf("   -R              : use 'read()' instead of 'take()'\n");
        printf("   --write-period <ms>: waiting period between 'write()' operations in ms.\n");
        printf("                        Default: 33ms\n");
        printf("   --read-period <ms> : waiting period between 'read()' or 'take()' operations\n");
        printf("                        in ms. Default: 100ms\n");
        printf("   --lifespan <int>     : indicates the lifespan of a sample in ms\n");
        printf("   --num-iterations <int>: indicates the number of iterations of the main loop\n");
        printf("                           After that, the application will exit.\n");
        printf("                           Default: infinite\n");
        printf("   --num-instances <int>: indicates the number of instances a DataWriter writes.\n");
        printf("                          If the value is > 1, the additional instances are\n");
        printf("                          created by appending a number. For example, if the\n");
        printf("                          original color is \"BLUE\" the instances used are\n");
        printf("                           \"BLUE\", \"BLUE1\", \"BLUE2\"...\n");
        printf("   --num-topics <int>: indicates the number of topics created (using the same\n");
        printf("                       type). This also creates a DataReader or DataWriter per\n");
        printf("                       topic. If the value is > 1, the additional topic names\n");
        printf("                       are created by appending a number: For example, if the\n");
        printf("                       original topic name is \"Square\", the topics created are\n");
        printf("                       \"Square\", \"Square1\", \"Square2\"...\n");
        printf("   --final-instance-state [u|d]: indicates the action performed after the\n");
        printf("                                 DataWriter finishes its execution (before\n");
        printf("                                 deleting it):\n");
        printf("                                   - u: unregister\n");
        printf("                                   - d: dispose\n");
        printf("   --access-scope [i|t|g]: sets Presentation.access_scope to INSTANCE, TOPIC\n");
        printf("                           or GROUP\n");
        printf("   --coherent            : sets Presentation.coherent_access = true\n");
        printf("   --ordered             : sets Presentation.ordered_access = true\n");
        printf("   --coherent-sample-count <int>: amount of samples sent for each DataWriter and\n");
        printf("                                  instance that are grouped in a coherent set\n");
        printf("   --additional-payload-size <bytes>: indicates the amount of bytes added to the\n");
        printf("                                      samples written (for example to use large\n");
        printf("                                      data)\n");
        printf("   --take-read           : uses take()/read() instead of take_next_instance()\n");
        printf("                           read_next_instance()\n");
    }

    //-------------------------------------------------------------
    bool validate() {
        if (topic_name == NULL) {
            logger.log_message("please specify topic name [-t]", Verbosity::ERROR);
            return false;
        }
        if ( (!publish) && (!subscribe) ) {
            logger.log_message("please specify publish [-P] or subscribe [-S]", Verbosity::ERROR);
            return false;
        }
        if ( publish && subscribe ) {
            logger.log_message("please specify only one of: publish [-P] or subscribe [-S]", Verbosity::ERROR);
            return false;
        }
        if (publish && (color == NULL) ) {
            color = strdup("BLUE");
            logger.log_message("warning: color was not specified, defaulting to \"BLUE\"", Verbosity::ERROR);
        }
        if (publish && timebasedfilter_interval > 0) {
            logger.log_message("warning: time base filter [-i] ignored on publisher applications", Verbosity::ERROR);
        }
        if (publish && use_read == false ) {
            logger.log_message("warning: use read [-R] ignored on publisher applications", Verbosity::ERROR);
        }
        if (publish && take_read_next_instance == false ) {
            logger.log_message("warning: --take-read ignored on publisher applications", Verbosity::ERROR);
        }
        if (subscribe && shapesize != 20) {
            logger.log_message("warning: shapesize [-z] ignored on subscriber applications", Verbosity::ERROR);
        }
        if (subscribe && lifespan_us > 0) {
            logger.log_message("warning: --lifespan ignored on subscriber applications", Verbosity::ERROR);
        }
        if (subscribe && num_instances > 1) {
            logger.log_message("warning: --num-instances ignored on subscriber applications", Verbosity::ERROR);
        }
        if (subscribe && (unregister || dispose)) {
            logger.log_message("warning: --final-instance-state ignored on subscriber applications", Verbosity::ERROR);
        }
        if (subscribe && coherent_set_sample_count > 0) {
            logger.log_message("warning: --coherent-sample-count ignored on subscriber applications", Verbosity::ERROR);
        }
        if (!coherent_set_enabled && !ordered_access_enabled && coherent_set_sample_count) {
            logger.log_message("warning: --coherent-sample-count ignored because not coherent, or ordered access enabled", Verbosity::ERROR);
        }
        if (subscribe && additional_payload_size > 0) {
            logger.log_message("warning: --additional-payload-size ignored on subscriber applications", Verbosity::ERROR);
        }
        if (!coherent_set_enabled && !ordered_access_enabled && coherent_set_access_scope_set) {
            logger.log_message("warning: --access-scope ignored because not coherent, or ordered access enabled", Verbosity::ERROR);
        }

        return true;
    }

    //-------------------------------------------------------------
    bool parse(int argc, char *argv[])
    {
        logger.log_message("Running parse() function", Verbosity::DEBUG);
        int opt;
        bool parse_ok = true;
        static struct option long_options[] = {
            {"help", no_argument, NULL, 'h'},
            {"write-period", required_argument, NULL, 'W'},
            {"read-period", required_argument, NULL, 'A'},
            {"final-instance-state", required_argument, NULL, 'M'},
            {"access-scope", required_argument, NULL, 'C'},
            {"coherent", no_argument, NULL, 'T'},
            {"ordered", no_argument, NULL, 'O'},
            {"coherent-sample-count", required_argument, NULL, 'H'},
            {"additional-payload-size", required_argument, NULL, 'B'},
            {"num-topics", required_argument, NULL, 'E'},
            {"lifespan", required_argument, NULL, 'l'},
            {"num-instances", required_argument, NULL, 'I'},
            {"num-iterations", required_argument, NULL, 'n'},
            {"take-read", no_argument, NULL, 'K'},
            {NULL, 0, NULL, 0 }
        };

        while ((opt = getopt_long(argc, argv, "hPSbrRwc:d:D:f:i:k:p:s:x:t:v:z:",
                long_options, NULL)) != -1) {
            switch (opt) {
            case 'v':
                if (optarg[0] != '\0') {
                    switch (optarg[0]) {
                    case 'd':
                        logger.verbosity(DEBUG);
                        break;
                    case 'e':
                        logger.verbosity(ERROR);
                        break;
                    default:
                        logger.log_message("unrecognized value for verbosity "
                                    + std::string(1, optarg[0]),
                                Verbosity::ERROR);
                        parse_ok = false;
                    }
                }
                break;
            case 'w':
                print_writer_samples = true;
                break;
            case 'b':
                reliability_kind = BEST_EFFORT_RELIABILITY_QOS;
                break;
            case 'R':
                use_read = true;
                break;
            case 'c':
                color = strdup(optarg);
                break;
            case 'd': {
                int converted_param = sscanf(optarg, "%d", &domain_id);
                if (converted_param == 0) {
                    logger.log_message("unrecognized value for domain_id "
                                    + std::string(1, optarg[0]),
                            Verbosity::ERROR);
                    parse_ok = false;
                } else if (domain_id < 0) {
                    logger.log_message("incorrect value for domain_id "
                                + std::to_string(domain_id),
                            Verbosity::ERROR);
                    parse_ok = false;
                }
                break;
            }
            case 'D':
            if (optarg[0] != '\0') {
                switch (optarg[0]) {
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
                    logger.log_message("unrecognized value for durability "
                                + std::string(1, optarg[0]),
                            Verbosity::ERROR);
                        parse_ok = false;
                }
            }
            break;
            case 'i': {
                int converted_param = sscanf(optarg, "%d", &timebasedfilter_interval);
                if (converted_param == 0) {
                    logger.log_message("unrecognized value for timebasedfilter_interval "
                                + std::string(1, optarg[0]),
                            Verbosity::ERROR);
                    parse_ok = false;
                } else if (timebasedfilter_interval < 0) {
                    logger.log_message("incorrect value for timebasedfilter_interval "
                                + std::to_string(timebasedfilter_interval),
                            Verbosity::ERROR);
                    parse_ok = false;
                }
                break;
            }
            case 'f': {
                int converted_param = sscanf(optarg, "%d", &deadline_interval);
                if (converted_param == 0) {
                    logger.log_message("unrecognized value for deadline_interval "
                                    + std::string(1, optarg[0]),
                            Verbosity::ERROR);
                    parse_ok = false;
                } else if (deadline_interval < 0) {
                    logger.log_message("incorrect value for deadline_interval "
                                    + std::to_string(deadline_interval),
                            Verbosity::ERROR);
                    parse_ok = false;
                }
                break;
            }
            case 'k': {
                int converted_param = sscanf(optarg, "%d", &history_depth);
                if (converted_param == 0){
                    logger.log_message("unrecognized value for history_depth "
                                    + std::string(1, optarg[0]),
                            Verbosity::ERROR);
                    parse_ok = false;
                } else if (history_depth < 0) {
                    logger.log_message("incorrect value for history_depth "
                                    + std::to_string(history_depth),
                            Verbosity::ERROR);
                    parse_ok = false;
                }
                break;
            }
            case 'p':
                partition = strdup(optarg);
                break;
            case 'r':
                reliability_kind = RELIABLE_RELIABILITY_QOS;
                break;
            case 's': {
                int converted_param = sscanf(optarg, "%d", &ownership_strength);
                if (converted_param == 0){
                    logger.log_message("unrecognized value for ownership_strength "
                                    + std::string(1, optarg[0]),
                            Verbosity::ERROR);
                    parse_ok = false;
                } else if (ownership_strength < -1) {
                    logger.log_message("incorrect value for ownership_strength "
                                    + std::to_string(ownership_strength),
                            Verbosity::ERROR);
                    parse_ok = false;
                }
                break;
            }
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
            case 'x':
                if (optarg[0] != '\0') {
                    switch (optarg[0]) {
                    case '1':
                        data_representation = XCDR_DATA_REPRESENTATION;
                        break;
                    case '2':
                        data_representation = XCDR2_DATA_REPRESENTATION;
                        break;
                    default:
                        logger.log_message("unrecognized value for data representation "
                                    + std::string(1, optarg[0]),
                                Verbosity::ERROR);
                        parse_ok = false;
                    }
                }
                break;
            case 'z': {
                int converted_param = sscanf(optarg, "%d", &shapesize);
                if (converted_param == 0) {
                    logger.log_message("unrecognized value for shapesize "
                                + std::string(1, optarg[0]),
                            Verbosity::ERROR);
                    parse_ok = false;
                } else if (shapesize < 0) {
                    logger.log_message("incorrect value for shapesize "
                                    + std::to_string(shapesize),
                            Verbosity::ERROR);
                    parse_ok = false;
                }
                break;
            }
            case 'W': {
                int converted_param = 0;
                if (sscanf(optarg, "%d", &converted_param) == 0) {
                    logger.log_message("unrecognized value for write-period "
                                + std::string(1, optarg[0]),
                            Verbosity::ERROR);
                    parse_ok = false;
                } else if (converted_param < 0) {
                    logger.log_message("incorrect value for write-period "
                                + std::to_string(converted_param),
                            Verbosity::ERROR);
                    parse_ok = false;
                }
                write_period_us = (useconds_t) converted_param * 1000;
                break;
            }
            case 'A': {
                int converted_param = 0;
                if (sscanf(optarg, "%d", &converted_param) == 0) {
                    logger.log_message("unrecognized value for read-period "
                                + std::string(1, optarg[0]),
                            Verbosity::ERROR);
                    parse_ok = false;
                } else if (converted_param < 0) {
                    logger.log_message("incorrect value for read-period "
                                + std::to_string(converted_param),
                            Verbosity::ERROR);
                    parse_ok = false;
                }
                read_period_us = (useconds_t) converted_param * 1000;
                break;
            }
            case 'n': {
                if (sscanf(optarg, "%u", &num_iterations) == 0) {
                    logger.log_message("unrecognized value for num-iterations "
                                + std::string(1, optarg[0]),
                            Verbosity::ERROR);
                    parse_ok = false;
                } else if (num_iterations < 1) {
                    logger.log_message("incorrect value for num-iterations, "
                            "it must be >=1 "
                                + std::to_string(num_iterations),
                            Verbosity::ERROR);
                    parse_ok = false;
                }
                break;
            }
            case 'l': {
                int converted_param = 0;
                if (sscanf(optarg, "%d", &converted_param) == 0) {
                    logger.log_message("unrecognized value for lifespan "
                                + std::string(1, optarg[0]),
                            Verbosity::ERROR);
                    parse_ok = false;
                } else if (converted_param < 0) {
                    logger.log_message("incorrect value for lifespan "
                                + std::to_string(converted_param),
                            Verbosity::ERROR);
                    parse_ok = false;
                }
                lifespan_us = converted_param * 1000;
                break;
            }
            case 'M': {
                if (optarg[0] != '\0') {
                    switch (optarg[0]) {
                    case 'u':
                        unregister = true;
                        break;
                    case 'd':
                        dispose = true;
                        break;
                    default:
                        logger.log_message("unrecognized value for final-instance-state "
                                    + std::string(1, optarg[0]),
                                Verbosity::ERROR);
                            parse_ok = false;
                    }
                    if (unregister && dispose) {
                        logger.log_message("error, cannot configure unregister and "
                                "dispose at the same time",
                                Verbosity::ERROR);
                            parse_ok = false;
                    }
                }
                break;
            }
            case 'C': {
                coherent_set_access_scope_set = true;
                if (optarg[0] != '\0') {
                    switch (optarg[0]) {
                    case 'i':
                        coherent_set_access_scope = INSTANCE_PRESENTATION_QOS;
                        break;
                    case 't':
                        coherent_set_access_scope = TOPIC_PRESENTATION_QOS;
                        break;
                    case 'g':
                        coherent_set_access_scope = GROUP_PRESENTATION_QOS;
                        break;
                    default:
                        logger.log_message("unrecognized value for coherent-sets "
                                + std::string(1, optarg[0]),
                            Verbosity::ERROR);
                        parse_ok = false;
                        coherent_set_access_scope_set = false;
                    }
                }
                break;
            }
            case 'T': {
                coherent_set_enabled = true;
                break;
            }
            case 'O': {
                ordered_access_enabled = true;
                break;
            }
            case 'I': {
                if (sscanf(optarg, "%u", &num_instances) == 0) {
                    logger.log_message("unrecognized value for num-instances "
                                + std::string(1, optarg[0]),
                            Verbosity::ERROR);
                    parse_ok = false;
                } else if (num_instances < 1) {
                    logger.log_message("incorrect value for num-instances, "
                            "it must be >=1 "
                                + std::to_string(num_instances),
                            Verbosity::ERROR);
                    parse_ok = false;
                }
                break;
            }
            case 'E': {
                if (sscanf(optarg, "%u", &num_topics) == 0) {
                    logger.log_message("unrecognized value for num-topics "
                                + std::string(1, optarg[0]),
                            Verbosity::ERROR);
                    parse_ok = false;
                } else if (num_topics < 1) {
                    logger.log_message("incorrect value for num-topics, "
                            "it must be >=1 "
                                + std::to_string(num_topics),
                            Verbosity::ERROR);
                    parse_ok = false;
                }
                break;
            }
            case 'B': {
                if (sscanf(optarg, "%u", &additional_payload_size) == 0) {
                    logger.log_message("unrecognized value for additional-payload-size "
                                + std::string(1, optarg[0]),
                            Verbosity::ERROR);
                    parse_ok = false;
                } else if (additional_payload_size < 1) {
                    logger.log_message("incorrect value for additional-payload-size, "
                            "it must be >=1 "
                                + std::to_string(additional_payload_size),
                            Verbosity::ERROR);
                    parse_ok = false;
                }
                break;
            }
            case 'H': {
                if (sscanf(optarg, "%u", &coherent_set_sample_count) == 0) {
                    logger.log_message("unrecognized value for coherent-sample-count "
                                + std::string(1, optarg[0]),
                            Verbosity::ERROR);
                    parse_ok = false;
                } else if (coherent_set_sample_count < 2) {
                    logger.log_message("incorrect value for coherent-sample-count, "
                            "it must be >=2 "
                                + std::to_string(coherent_set_sample_count),
                            Verbosity::ERROR);
                    parse_ok = false;
                }
                break;
            }
            case 'K' :
                take_read_next_instance = false;
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
        } else {
            std::string app_kind = publish ? "publisher" : "subscriber";
            logger.log_message("Shape Options: "
                    "\n    Verbosity = " + QosUtils::to_string(logger.verbosity()) +
                    "\n    This application is a " + app_kind +
                    "\n    DomainId = " + std::to_string(domain_id) +
                    "\n    ReliabilityKind = " + QosUtils::to_string(reliability_kind) +
                    "\n    DurabilityKind = " + QosUtils::to_string(durability_kind) +
                    "\n    DataRepresentation = " + QosUtils::to_string(data_representation) +
                    "\n    HistoryDepth = " + std::to_string(history_depth) +
                    "\n    OwnershipStrength = " + std::to_string(ownership_strength) +
                    "\n    TimeBasedFilterInterval = " + std::to_string(timebasedfilter_interval) +
                    "\n    DeadlineInterval = " + std::to_string(deadline_interval) +
                    "\n    Shapesize = " + std::to_string(shapesize) +
                    "\n    Reading method = " + (use_read ? "read_next_instance" : "take_next_instance") +
                    "\n    Write period = " + std::to_string(write_period_us / 1000) + "ms" +
                    "\n    Read period = " + std::to_string(read_period_us / 1000) + "ms" +
                    "\n    Lifespan: " + std::to_string(lifespan_us / 1000) + "ms" +
                    "\n    Number of iterations = " + std::to_string(num_iterations) +
                    "\n    Number of instances: " + std::to_string(num_instances) +
                    "\n    Number of entities: " + std::to_string(num_topics) +
                    "\n    Coherent sets: " + (coherent_set_enabled ? "true" : "false") +
                    "\n    Ordered access: " + (ordered_access_enabled ? "true" : "false") +
                    "\n    Access Scope: " + QosUtils::to_string(coherent_set_access_scope) +
                    "\n    Coherent Sample Count: " + std::to_string(coherent_set_sample_count) +
                    "\n    Additional Payload Size: " + std::to_string(additional_payload_size) +
                    "\n    Final Instance State: "
                            + (unregister ? "Unregister" : (dispose ? "Dispose" : "not specified")),
                    Verbosity::DEBUG);
            if (topic_name != NULL){
                logger.log_message("    Topic = " + std::string(topic_name),
                        Verbosity::DEBUG);
            }
            if (color != NULL) {
                logger.log_message("    Color = " + std::string(color),
                        Verbosity::DEBUG);
            }
            if (partition != NULL) {
                logger.log_message("    Partition = " + std::string(partition), Verbosity::DEBUG);
            }
        }
        return parse_ok;
    }
};

/*************************************************************/
class DPListener : public DomainParticipantListener
{
public:
    void on_inconsistent_topic         (Topic *topic,  const InconsistentTopicStatus &) {
        const char *topic_name = topic->get_name() NAME_ACCESSOR;
        const char *type_name  = topic->get_type_name() NAME_ACCESSOR;
        printf("%s() topic: '%s'  type: '%s'\n", __FUNCTION__, topic_name, type_name);
    }

    void on_offered_incompatible_qos(DataWriter *dw,  const OfferedIncompatibleQosStatus & status) {
        Topic      *topic       = dw->get_topic( );
        const char *topic_name  = topic->get_name() NAME_ACCESSOR;
        const char *type_name   = topic->get_type_name() NAME_ACCESSOR;
        const char *policy_name = NULL;
        policy_name = get_qos_policy_name(status.last_policy_id);
        printf("%s() topic: '%s'  type: '%s' : %d (%s)\n", __FUNCTION__,
                topic_name, type_name,
                status.last_policy_id,
                policy_name );
    }

    void on_publication_matched (DataWriter *dw, const PublicationMatchedStatus & status) {
        Topic      *topic      = dw->get_topic( );
        const char *topic_name = topic->get_name() NAME_ACCESSOR;
        const char *type_name  = topic->get_type_name() NAME_ACCESSOR;
        printf("%s() topic: '%s'  type: '%s' : matched readers %d (change = %d)\n", __FUNCTION__,
                topic_name, type_name, status.current_count, status.current_count_change);
    }

    void on_offered_deadline_missed (DataWriter *dw, const OfferedDeadlineMissedStatus & status) {
        Topic      *topic      = dw->get_topic( );
        const char *topic_name = topic->get_name() NAME_ACCESSOR;
        const char *type_name  = topic->get_type_name() NAME_ACCESSOR;
        printf("%s() topic: '%s'  type: '%s' : (total = %d, change = %d)\n", __FUNCTION__,
                topic_name, type_name, status.total_count, status.total_count_change);
    }

    void on_liveliness_lost (DataWriter *dw, const LivelinessLostStatus & status) {
        Topic      *topic      = dw->get_topic( );
        const char *topic_name = topic->get_name() NAME_ACCESSOR;
        const char *type_name  = topic->get_type_name() NAME_ACCESSOR;
        printf("%s() topic: '%s'  type: '%s' : (total = %d, change = %d)\n", __FUNCTION__,
                topic_name, type_name, status.total_count, status.total_count_change);
    }

    void on_requested_incompatible_qos (DataReader *dr, const RequestedIncompatibleQosStatus & status) {
        TopicDescription *td         = GET_TOPIC_DESCRIPTION(dr);
        const char       *topic_name = td->get_name() NAME_ACCESSOR;
        const char       *type_name  = td->get_type_name() NAME_ACCESSOR;
        const char *policy_name = NULL;
        policy_name = get_qos_policy_name(status.last_policy_id);
        printf("%s() topic: '%s'  type: '%s' : %d (%s)\n", __FUNCTION__,
                topic_name, type_name, status.last_policy_id,
                policy_name);
    }

    void on_subscription_matched (DataReader *dr, const SubscriptionMatchedStatus & status) {
        TopicDescription *td         = GET_TOPIC_DESCRIPTION(dr);
        const char       *topic_name = td->get_name() NAME_ACCESSOR;
        const char       *type_name  = td->get_type_name() NAME_ACCESSOR;
        printf("%s() topic: '%s'  type: '%s' : matched writers %d (change = %d)\n", __FUNCTION__,
                topic_name, type_name, status.current_count, status.current_count_change);
    }

    void on_requested_deadline_missed (DataReader *dr, const RequestedDeadlineMissedStatus & status) {
        TopicDescription *td         = GET_TOPIC_DESCRIPTION(dr);
        const char       *topic_name = td->get_name() NAME_ACCESSOR;
        const char       *type_name  = td->get_type_name() NAME_ACCESSOR;
        printf("%s() topic: '%s'  type: '%s' : (total = %d, change = %d)\n", __FUNCTION__,
                topic_name, type_name, status.total_count, status.total_count_change);
    }

    void on_liveliness_changed (DataReader *dr, const LivelinessChangedStatus & status) {
        TopicDescription *td         = GET_TOPIC_DESCRIPTION(dr);
        const char       *topic_name = td->get_name() NAME_ACCESSOR;
        const char       *type_name  = td->get_type_name() NAME_ACCESSOR;
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
    Topic                    **topics;
    ShapeTypeDataReader      **drs;
    ShapeTypeDataWriter      **dws;

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

        free(topics);
        free(drs);
        free(dws);

        STRING_FREE(color);
    }

    //-------------------------------------------------------------
    bool initialize(ShapeOptions *options)
    {
        // Initialize entities array
        topics = (Topic**) malloc(sizeof(Topic*) * options->num_topics);
        if (topics == NULL) {
            logger.log_message("Error allocating memory for topics", Verbosity::ERROR);
            return false;
        }
        for (unsigned int i = 0; i < options->num_topics; ++i) {
            topics[i] = NULL;
        }

        drs = (ShapeTypeDataReader**) malloc(sizeof(ShapeTypeDataReader*) * options->num_topics);
        if (drs == NULL) {
            logger.log_message("Error allocating memory for DataReaders", Verbosity::ERROR);
            return false;
        }
        for (unsigned int i = 0; i < options->num_topics; ++i) {
            drs[i] = NULL;
        }

        dws = (ShapeTypeDataWriter**) malloc(sizeof(ShapeTypeDataWriter*) * options->num_topics);
        if (dws == NULL) {
            logger.log_message("Error allocating memory for DataWriters", Verbosity::ERROR);
            return false;
        }
        for (unsigned int i = 0; i < options->num_topics; ++i) {
            dws[i] = NULL;
        }

#ifndef OBTAIN_DOMAIN_PARTICIPANT_FACTORY
#define OBTAIN_DOMAIN_PARTICIPANT_FACTORY DomainParticipantFactory::get_instance()
#endif
        logger.log_message("Running initialize() function", Verbosity::DEBUG);

        DomainParticipantFactory *dpf = OBTAIN_DOMAIN_PARTICIPANT_FACTORY;
        if (dpf == NULL) {
            logger.log_message("failed to create participant factory (missing license?).", Verbosity::ERROR);
            return false;
        }
        logger.log_message("Participant Factory created", Verbosity::DEBUG);
#ifdef CONFIGURE_PARTICIPANT_FACTORY
        CONFIGURE_PARTICIPANT_FACTORY
#endif

        dp = dpf->create_participant( options->domain_id, PARTICIPANT_QOS_DEFAULT, &dp_listener, LISTENER_STATUS_MASK_ALL );
        if (dp == NULL) {
            logger.log_message("failed to create participant (missing license?).", Verbosity::ERROR);
            return false;
        }
        logger.log_message("Participant created", Verbosity::DEBUG);
#ifndef REGISTER_TYPE
#define REGISTER_TYPE ShapeTypeTypeSupport::register_type
#endif
        REGISTER_TYPE(dp, "ShapeType");

        // Create different topics (depending on the number of entities)
        // being the first topic name the provide one, and the rest appending
        // a number after, for example: Square, Square1, Square2...
        for (unsigned int i = 0; i < options->num_topics; ++i) {
            std::string topic_name;
            topic_name = std::string(options->topic_name) + (i > 0 ? std::to_string(i) : "");
            printf("Create topic: %s\n", topic_name.c_str());
            topics[i] = dp->create_topic( topic_name.c_str(), "ShapeType", TOPIC_QOS_DEFAULT, NULL, LISTENER_STATUS_MASK_NONE);
            if (topics[i] == NULL) {
                logger.log_message("failed to create topic <" + topic_name + ">", Verbosity::ERROR);
                return false;
            }
        }
        logger.log_message("Topics created:", Verbosity::DEBUG);
        for (unsigned int i = 0; i < options->num_topics; ++i) {
            if (logger.verbosity() == Verbosity::DEBUG) {
                printf("    topic[%d]=%p\n",i,(void*)topics[i]);
            }
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
        logger.log_message("Running run() function", Verbosity::DEBUG);
        if ( pub != NULL ) {
            return run_publisher(options);
        }
        else if ( sub != NULL ) {
            return run_subscriber(options);
        }

        return false;
    }

    //-------------------------------------------------------------
    bool init_publisher(ShapeOptions *options)
    {
        logger.log_message("Running init_publisher() function", Verbosity::DEBUG);
        PublisherQos  pub_qos;
        DataWriterQos dw_qos;

        dp->get_default_publisher_qos( pub_qos );
        if ( options->partition != NULL ) {
            ADD_PARTITION(pub_qos.partition, options->partition);
        }

        logger.log_message("Publisher QoS:", Verbosity::DEBUG);

#if   defined(RTI_CONNEXT_DDS)
        if (options->coherent_set_enabled) {
            pub_qos.presentation.coherent_access = DDS_BOOLEAN_TRUE;
        }
        if (options->ordered_access_enabled) {
            pub_qos.presentation.ordered_access = DDS_BOOLEAN_TRUE;
        }
        if (options->ordered_access_enabled || options->coherent_set_enabled) {
            pub_qos.presentation.access_scope = options->coherent_set_access_scope;
        }

        logger.log_message("    Presentation Coherent Access = " +
                std::string(pub_qos.presentation.coherent_access ? "true" : "false"), Verbosity::DEBUG);
        logger.log_message("    Presentation Ordered Access = " +
                std::string(pub_qos.presentation.ordered_access ? "true" : "false"), Verbosity::DEBUG);
        logger.log_message("    Presentation Access Scope = " +
                QosUtils::to_string(pub_qos.presentation.access_scope), Verbosity::DEBUG);
#else
        logger.log_message("    Presentation Coherent Access = Not supported", Verbosity::ERROR);
        logger.log_message("    Presentation Ordered Access = Not supported", Verbosity::ERROR);
        logger.log_message("    Presentation Access Scope = Not supported", Verbosity::ERROR);
#endif

        pub = dp->create_publisher(pub_qos, NULL, LISTENER_STATUS_MASK_NONE);
        if (pub == NULL) {
            logger.log_message("failed to create publisher", Verbosity::ERROR);
            return false;
        }
        logger.log_message("Publisher created", Verbosity::DEBUG);
        logger.log_message("Data Writer QoS:", Verbosity::DEBUG);
        pub->get_default_datawriter_qos( dw_qos );
        dw_qos.reliability FIELD_ACCESSOR.kind = options->reliability_kind;
        logger.log_message("    Reliability = " + QosUtils::to_string(dw_qos.reliability FIELD_ACCESSOR.kind), Verbosity::DEBUG);
        dw_qos.durability FIELD_ACCESSOR.kind  = options->durability_kind;
        logger.log_message("    Durability = " + QosUtils::to_string(dw_qos.durability FIELD_ACCESSOR.kind), Verbosity::DEBUG);

#if   defined(RTI_CONNEXT_DDS)
        DataRepresentationIdSeq data_representation_seq;
        data_representation_seq.ensure_length(1,1);
        data_representation_seq[0] = options->data_representation;
        dw_qos.representation.value = data_representation_seq;

#elif  defined(TWINOAKS_COREDX)
        dw_qos.rtps_writer.apply_filters = 0;
        dw_qos.representation.value.clear( );
        dw_qos.representation.value.push_back( options->data_representation );

#elif  defined(INTERCOM_DDS)
        dw_qos.representation.value.clear( );
        dw_qos.representation.value.push_back( options->data_representation );

#elif   defined(OPENDDS)
        dw_qos.representation.value.length(1);
        dw_qos.representation.value[0] = options->data_representation;

#elif  defined(EPROSIMA_FAST_DDS)
        dw_qos.representation().m_value.clear( );
        dw_qos.representation().m_value.push_back( options->data_representation );
#endif

#if  defined(EPROSIMA_FAST_DDS)
        logger.log_message("    Data_Representation = " + QosUtils::to_string(dw_qos.representation  FIELD_ACCESSOR.m_value[0]), Verbosity::DEBUG);
#else
        logger.log_message("    Data_Representation = " + QosUtils::to_string(dw_qos.representation  FIELD_ACCESSOR.value[0]), Verbosity::DEBUG);
#endif

        if ( options->ownership_strength != -1 ) {
            dw_qos.ownership FIELD_ACCESSOR.kind = EXCLUSIVE_OWNERSHIP_QOS;
            dw_qos.ownership_strength FIELD_ACCESSOR.value = options->ownership_strength;
        }

        if ( options->ownership_strength == -1 ) {
            dw_qos.ownership  FIELD_ACCESSOR.kind = SHARED_OWNERSHIP_QOS;
        }
        logger.log_message("    Ownership = " + QosUtils::to_string(dw_qos.ownership FIELD_ACCESSOR.kind), Verbosity::DEBUG);
        if (dw_qos.ownership FIELD_ACCESSOR.kind == EXCLUSIVE_OWNERSHIP_QOS){
            logger.log_message("    OwnershipStrength = " + std::to_string(dw_qos.ownership_strength FIELD_ACCESSOR.value), Verbosity::DEBUG);
        }

        if ( options->deadline_interval > 0 ) {
            dw_qos.deadline FIELD_ACCESSOR.period.SECONDS_FIELD_NAME = options->deadline_interval;
            dw_qos.deadline FIELD_ACCESSOR.period.nanosec  = 0;
        }
        logger.log_message("    DeadlinePeriod = " + std::to_string(dw_qos.deadline FIELD_ACCESSOR.period.SECONDS_FIELD_NAME), Verbosity::DEBUG);

        // options->history_depth < 0 means leave default value
        if ( options->history_depth > 0 )  {
            dw_qos.history FIELD_ACCESSOR.kind  = KEEP_LAST_HISTORY_QOS;
            dw_qos.history FIELD_ACCESSOR.depth = options->history_depth;
        }
        else if ( options->history_depth == 0 ) {
            dw_qos.history FIELD_ACCESSOR.kind  = KEEP_ALL_HISTORY_QOS;
        }
        logger.log_message("    History = " + QosUtils::to_string(dw_qos.history FIELD_ACCESSOR.kind), Verbosity::DEBUG);
        if (dw_qos.history FIELD_ACCESSOR.kind == KEEP_LAST_HISTORY_QOS){
            logger.log_message("    HistoryDepth = " + std::to_string(dw_qos.history FIELD_ACCESSOR.depth), Verbosity::DEBUG);
        }

#if   defined(RTI_CONNEXT_DDS)
        if (options->lifespan_us > 0) {
            dw_qos.lifespan.duration = dw_qos.lifespan.duration.from_micros(options->lifespan_us);
        }
        logger.log_message("    Lifespan = " + std::to_string(dw_qos.lifespan.duration.SECONDS_FIELD_NAME) + " secs", Verbosity::DEBUG);
        logger.log_message("               " + std::to_string(dw_qos.lifespan.duration.nanosec) + " nanosecs", Verbosity::DEBUG);
#elif  defined(EPROSIMA_FAST_DDS)
        if (options->lifespan_us > 0) {
            dw_qos.lifespan FIELD_ACCESSOR.duration = Duration_t(options->lifespan_us * 1e-6);
        }
        logger.log_message("    Lifespan = " + std::to_string(dw_qos.lifespan FIELD_ACCESSOR.duration.seconds) + " secs", Verbosity::DEBUG);
        logger.log_message("               " + std::to_string(dw_qos.lifespan FIELD_ACCESSOR.duration.nanosec) + " nanosecs", Verbosity::DEBUG);

#else
        logger.log_message("    Lifespan = Not supported", Verbosity::ERROR);
#endif

#if   defined(RTI_CONNEXT_DDS)
        // usage of large data
        if (options->additional_payload_size > 64000) {
            dw_qos.publish_mode.kind = ASYNCHRONOUS_PUBLISH_MODE_QOS;
        }
        logger.log_message("    Publish Mode kind = "
                + std::string(dw_qos.publish_mode.kind == ASYNCHRONOUS_PUBLISH_MODE_QOS
                        ? "ASYNCHRONOUS_PUBLISH_MODE_QOS" : "SYNCHRONOUS_PUBLISH_MODE_QOS"), Verbosity::DEBUG);
#endif

#if   defined(RTI_CONNEXT_DDS)
        if (options->unregister) {
            dw_qos.writer_data_lifecycle.autodispose_unregistered_instances = DDS_BOOLEAN_FALSE;
        }
        logger.log_message("    Autodispose_unregistered_instances = "
                + std::string(dw_qos.writer_data_lifecycle.autodispose_unregistered_instances ? "true" : "false"), Verbosity::DEBUG);
#elif defined(EPROSIMA_FAST_DDS)
        if (options->unregister) {
            dw_qos.writer_data_lifecycle FIELD_ACCESSOR .autodispose_unregistered_instances = false;
        }
        logger.log_message("    Autodispose_unregistered_instances = "
            + std::string(dw_qos.writer_data_lifecycle FIELD_ACCESSOR .autodispose_unregistered_instances ? "true" : "false"), Verbosity::DEBUG);
#else
        logger.log_message("    Autodispose_unregistered_instances = Not supported", Verbosity::ERROR);
#endif

        // Create different DataWriters (depending on the number of entities)
        // The DWs are attached to the same array index of the topics.
        for (unsigned int i = 0; i < options->num_topics; ++i) {
            printf("Create writer for topic: %s color: %s\n", topics[i]->get_name() NAME_ACCESSOR, options->color );
            dws[i] = dynamic_cast<ShapeTypeDataWriter *>(pub->create_datawriter( topics[i], dw_qos, NULL, LISTENER_STATUS_MASK_NONE));
            if (dws[i] == NULL) {
                logger.log_message("failed to create datawriter[" + std::to_string(i) + "] topic: " + topics[i]->get_name(), Verbosity::ERROR);
                return false;
            }
        }

        logger.log_message("DataWriters created:", Verbosity::DEBUG);
        for (unsigned int i = 0; i < options->num_topics; ++i) {
            if (logger.verbosity() == Verbosity::DEBUG) {
                printf("    dws[%d]=%p\n",i,(void*)dws[i]);
            }
        }

        color = strdup(options->color);
        xvel = options->xvel;
        yvel = options->yvel;
        da_width  = options->da_width;
        da_height = options->da_height;
        logger.log_message("Data Writer created", Verbosity::DEBUG);
        logger.log_message("Color " + std::string(color), Verbosity::DEBUG);
        logger.log_message("xvel " + std::to_string(xvel), Verbosity::DEBUG);
        logger.log_message("yvel " + std::to_string(yvel), Verbosity::DEBUG);
        logger.log_message("da_width " + std::to_string(da_width), Verbosity::DEBUG);
        logger.log_message("da_height " + std::to_string(da_height), Verbosity::DEBUG);

        return true;
    }

    //-------------------------------------------------------------
    bool init_subscriber(ShapeOptions *options)
    {
        logger.log_message("Running init_subscriber() function", Verbosity::DEBUG);
        SubscriberQos sub_qos;
        DataReaderQos dr_qos;

        dp->get_default_subscriber_qos( sub_qos );
        if ( options->partition != NULL ) {
            ADD_PARTITION(sub_qos.partition, options->partition);
        }

        logger.log_message("Subscriber QoS:", Verbosity::DEBUG);

#if   defined(RTI_CONNEXT_DDS)
        if (options->coherent_set_enabled) {
            sub_qos.presentation.coherent_access = DDS_BOOLEAN_TRUE;
        }
        if (options->ordered_access_enabled) {
            sub_qos.presentation.ordered_access = DDS_BOOLEAN_TRUE;
        }
        if (options->ordered_access_enabled || options->coherent_set_enabled) {
            sub_qos.presentation.access_scope = options->coherent_set_access_scope;
        }

        logger.log_message("    Presentation Coherent Access = " +
                std::string(sub_qos.presentation.coherent_access ? "true" : "false"), Verbosity::DEBUG);
        logger.log_message("    Presentation Ordered Access = " +
                std::string(sub_qos.presentation.ordered_access ? "true" : "false"), Verbosity::DEBUG);
        logger.log_message("    Presentation Access Scope = " +
                QosUtils::to_string(sub_qos.presentation.access_scope), Verbosity::DEBUG);

#else
        logger.log_message("    Presentation Coherent Access = Not supported", Verbosity::ERROR);
        logger.log_message("    Presentation Ordered Access = Not supported", Verbosity::ERROR);
        logger.log_message("    Presentation Access Scope = Not supported", Verbosity::ERROR);
#endif

        sub = dp->create_subscriber( sub_qos, NULL, LISTENER_STATUS_MASK_NONE );
        if (sub == NULL) {
            logger.log_message("failed to create subscriber", Verbosity::ERROR);
            return false;
        }
        logger.log_message("Subscriber created", Verbosity::DEBUG);
        logger.log_message("Data Reader QoS:", Verbosity::DEBUG);
        sub->get_default_datareader_qos( dr_qos );
        dr_qos.reliability FIELD_ACCESSOR.kind = options->reliability_kind;
        logger.log_message("    Reliability = " + QosUtils::to_string(dr_qos.reliability FIELD_ACCESSOR.kind), Verbosity::DEBUG);
        dr_qos.durability FIELD_ACCESSOR.kind  = options->durability_kind;
        logger.log_message("    Durability = " + QosUtils::to_string(dr_qos.durability FIELD_ACCESSOR.kind), Verbosity::DEBUG);

#if   defined(RTI_CONNEXT_DDS)
        DataRepresentationIdSeq data_representation_seq;
        data_representation_seq.ensure_length(1,1);
        data_representation_seq[0] = options->data_representation;
        dr_qos.representation.value = data_representation_seq;
#elif  defined(TWINOAKS_COREDX)
        dr_qos.rtps_reader.send_initial_nack = 1;
        dr_qos.rtps_reader.precache_max_samples = 0;
        dr_qos.representation.value.clear( );
        dr_qos.representation.value.push_back( options->data_representation );

#elif  defined(INTERCOM_DDS)
        dr_qos.representation.value.clear( );
        dr_qos.representation.value.push_back( options->data_representation );

#elif   defined(OPENDDS)
        dr_qos.representation.value.length(1);
        dr_qos.representation.value[0] = options->data_representation;

#elif   defined(EPROSIMA_FAST_DDS)
        dr_qos.representation().m_value.clear();
        dr_qos.representation().m_value.push_back( options->data_representation );
#endif

#if defined(EPROSIMA_FAST_DDS)
        logger.log_message("    DataRepresentation = " + QosUtils::to_string(dr_qos.representation().m_value[0]), Verbosity::DEBUG);
#else
        logger.log_message("    DataRepresentation = " + QosUtils::to_string(dr_qos.representation FIELD_ACCESSOR.value[0]), Verbosity::DEBUG);
#endif
        if ( options->ownership_strength != -1 ) {
            dr_qos.ownership FIELD_ACCESSOR.kind = EXCLUSIVE_OWNERSHIP_QOS;
        }
        logger.log_message("    Ownership = " + QosUtils::to_string(dr_qos.ownership FIELD_ACCESSOR.kind), Verbosity::DEBUG);
        if ( options->timebasedfilter_interval > 0) {
#if defined(EPROSIMA_FAST_DDS)
            logger.log_message("    Time based filter not supported", Verbosity::ERROR);
#else
            dr_qos.time_based_filter FIELD_ACCESSOR.minimum_separation.SECONDS_FIELD_NAME = options->timebasedfilter_interval;
            dr_qos.time_based_filter FIELD_ACCESSOR.minimum_separation.nanosec = 0;
#endif
        }
        logger.log_message("    TimeBasedFilter = " + std::to_string(dr_qos.time_based_filter FIELD_ACCESSOR.minimum_separation.SECONDS_FIELD_NAME), Verbosity::DEBUG);

        if ( options->deadline_interval > 0 ) {
            dr_qos.deadline FIELD_ACCESSOR.period.SECONDS_FIELD_NAME = options->deadline_interval;
            dr_qos.deadline FIELD_ACCESSOR.period.nanosec  = 0;
        }
        logger.log_message("    DeadlinePeriod = " + std::to_string(dr_qos.deadline FIELD_ACCESSOR.period.SECONDS_FIELD_NAME), Verbosity::DEBUG);

        // options->history_depth < 0 means leave default value
        if ( options->history_depth > 0 )  {
            dr_qos.history FIELD_ACCESSOR.kind  = KEEP_LAST_HISTORY_QOS;
            dr_qos.history FIELD_ACCESSOR.depth = options->history_depth;
        }
        else if ( options->history_depth == 0 ) {
            dr_qos.history FIELD_ACCESSOR.kind  = KEEP_ALL_HISTORY_QOS;
        }
        logger.log_message("    History = " + QosUtils::to_string(dr_qos.history FIELD_ACCESSOR.kind), Verbosity::DEBUG);
        if (dr_qos.history FIELD_ACCESSOR.kind == KEEP_LAST_HISTORY_QOS){
            logger.log_message("    HistoryDepth = " + std::to_string(dr_qos.history FIELD_ACCESSOR.depth), Verbosity::DEBUG);
        }

        if ( options->color != NULL ) {
            /*  filter on specified color */
            ContentFilteredTopic *cft = NULL;
            StringSeq             cf_params;

        for (unsigned int i = 0; i < options->num_topics; ++i) {
            const std::string filtered_topic_name_str =
                    std::string(options->topic_name) +
                    (i > 0 ? std::to_string(i) : "") +
                    "_filtered";
            const char* filtered_topic_name = filtered_topic_name_str.c_str();
#if   defined(RTI_CONNEXT_DDS)
                char parameter[64];
                snprintf(parameter, 64, "'%s'",  options->color);
                StringSeq_push(cf_params, parameter);

                cft = dp->create_contentfilteredtopic(filtered_topic_name, topics[i], "color = %0", cf_params);
                logger.log_message("    ContentFilterTopic = \"color = "
                    + std::string(parameter) + std::string("\""), Verbosity::DEBUG);
#elif defined(TWINOAKS_COREDX) || defined(OPENDDS)
                StringSeq_push(cf_params, options->color);
                cft = dp->create_contentfilteredtopic(filtered_topic_name, topics[i], "color = %0", cf_params);
                logger.log_message("    ContentFilterTopic = \"color = "
                    + std::string(options->color) + std::string("\""), Verbosity::DEBUG);

#elif defined(INTERCOM_DDS)
                char parameter[64];
                sprintf(parameter, "'%s'",  options->color);
                StringSeq_push(cf_params, parameter);
                cft = dp->create_contentfilteredtopic(filtered_topic_name, topics[i], "color = %0", cf_params);
                logger.log_message("    ContentFilterTopic = \"color = "
                    + std::string(parameter) + std::string("\""), Verbosity::DEBUG);

#elif defined(EPROSIMA_FAST_DDS)
                cf_params.push_back(std::string("'") + options->color + std::string("'"));
                cft = dp->create_contentfilteredtopic(filtered_topic_name, topics[i], "color = %0", cf_params);
                logger.log_message("    ContentFilterTopic = \"color = "
                    + cf_params[0] + std::string("\""), Verbosity::DEBUG);
#endif
                if (cft == NULL) {
                    logger.log_message("failed to create content filtered topic", Verbosity::ERROR);
                    return false;
                }

                printf("Create reader for topic: %s color: %s\n", cft->get_name() NAME_ACCESSOR, options->color );
                drs[i] = dynamic_cast<ShapeTypeDataReader *>(sub->create_datareader(cft, dr_qos, NULL, LISTENER_STATUS_MASK_NONE));
                if (drs[i] == NULL) {
                    logger.log_message("failed to create datareader[" + std::to_string(i) + "] topic: " + topics[i]->get_name(), Verbosity::ERROR);
                    return false;
                }
            }
        } else {
            // Create different DataReaders (depending on the number of entities)
            // The DRs are attached to the same array index of the topics.
            for (unsigned int i = 0; i < options->num_topics; ++i) {
                printf("Create reader for topic: %s\n", topics[i]->get_name() NAME_ACCESSOR);
                drs[i] = dynamic_cast<ShapeTypeDataReader *>(sub->create_datareader(topics[i], dr_qos, NULL, LISTENER_STATUS_MASK_NONE));
                if (drs[i] == NULL) {
                    logger.log_message("failed to create datareader[" + std::to_string(i) + "] topic: " + topics[i]->get_name(), Verbosity::ERROR);
                    return false;
                }
            }
        }
        logger.log_message("DataReaders created:", Verbosity::DEBUG);
        for (unsigned int i = 0; i < options->num_topics; ++i) {
            if (logger.verbosity() == Verbosity::DEBUG) {
                printf("    drs[%d]=%p\n",i,(void*)drs[i]);
            }
        }

        logger.log_message("Data Reader created", Verbosity::DEBUG);
        return true;
    }

    static void shape_set_color(ShapeType &shape, const char * color_value)
    {
#ifndef STRING_ASSIGN
        strcpy(shape.color STRING_INOUT, color_value);
#else
        STRING_ASSIGN(shape.color, color_value);
#endif
    }

    static void shape_initialize_w_color(ShapeType &shape, const char * color_value)
    {
#if defined(RTI_CONNEXT_DDS)
        ShapeType_initialize(&shape);
#endif

#ifndef STRING_ALLOC
#define STRING_ALLOC(A, B)
#endif

        STRING_ALLOC(shape.color, std::strlen(color_value));
        if (color_value != NULL) {
            shape_set_color(shape, color_value);
        }
    }

    //-------------------------------------------------------------
    bool run_subscriber(ShapeOptions *options)
    {
        // This is the number of iterations performed
        unsigned int n = 0;
        InstanceHandle_t *previous_handles = NULL;

        logger.log_message("Running run_subscriber() function", Verbosity::DEBUG);

        // Create a previous_handle per topic
        previous_handles = (InstanceHandle_t*) malloc(sizeof(InstanceHandle_t) * options->num_topics);
        if (previous_handles == NULL) {
            logger.log_message("Error allocating memory for previous_handles", Verbosity::ERROR);
            return false;
        }
#if  defined(EPROSIMA_FAST_DDS)
        // TODO: Remove when Fast DDS supports `get_key_value()`
        std::map<InstanceHandle_t, std::string> instance_handle_color;
#endif

        while ( ! all_done ) {
            ReturnCode_t     retval;
            SampleInfoSeq    sample_infos;

#if   defined(RTI_CONNEXT_DDS) || defined(OPENDDS) || defined(INTERCOM_DDS)
            ShapeTypeSeq          samples;
#elif defined(TWINOAKS_COREDX)
            ShapeTypePtrSeq       samples;
#elif defined(EPROSIMA_FAST_DDS)
            FASTDDS_CONST_SEQUENCE(DataSeq, ShapeType);
            DataSeq samples;
#endif

            if (options->coherent_set_enabled) {
                printf("Reading coherent sets, iteration %d\n",n);
            }
            if (options->ordered_access_enabled) {
                printf("Reading with ordered access, iteration %d\n",n);
            }
            if (options->coherent_set_enabled || options->ordered_access_enabled) {
                sub->begin_access();
            }
            for (unsigned int i = 0; i < options->num_topics; ++i) {
                previous_handles[i] = HANDLE_NIL;
                do {
                    if (!options->use_read) {
#if   defined(RTI_CONNEXT_DDS) || defined(OPENDDS) || defined(EPROSIMA_FAST_DDS) || defined(INTERCOM_DDS)
                        if (options->take_read_next_instance) {
                            logger.log_message("Calling take_next_instance() function", Verbosity::DEBUG);
                            retval = drs[i]->take_next_instance ( samples,
                                    sample_infos,
                                    LENGTH_UNLIMITED,
                                    previous_handles[i],
                                    ANY_SAMPLE_STATE,
                                    ANY_VIEW_STATE,
                                    ANY_INSTANCE_STATE );
                        } else {
                            logger.log_message("Calling take() function", Verbosity::DEBUG);
                            retval = drs[i]->take ( samples,
                                    sample_infos,
                                    LENGTH_UNLIMITED,
                                    ANY_SAMPLE_STATE,
                                    ANY_VIEW_STATE,
                                    ANY_INSTANCE_STATE );
                        }
#elif defined(TWINOAKS_COREDX)
                        if (options->take_read_next_instance) {
                            logger.log_message("Calling take_next_instance() function", Verbosity::DEBUG);
                            retval = drs[i]->take_next_instance ( &samples,
                                    &sample_infos,
                                    LENGTH_UNLIMITED,
                                    previous_handles[i],
                                    ANY_SAMPLE_STATE,
                                    ANY_VIEW_STATE,
                                    ANY_INSTANCE_STATE );
                        } else {
                            logger.log_message("Calling take() function", Verbosity::DEBUG);
                            retval = drs[i]->take ( &samples,
                                    &sample_infos,
                                    LENGTH_UNLIMITED,
                                    ANY_SAMPLE_STATE,
                                    ANY_VIEW_STATE,
                                    ANY_INSTANCE_STATE );
                        }
#endif
                    } else { /* Use read_next_instance*/
#if   defined(RTI_CONNEXT_DDS) || defined(OPENDDS) || defined(EPROSIMA_FAST_DDS) || defined(INTERCOM_DDS)
                        if (options->take_read_next_instance) {
                            logger.log_message("Calling read_next_instance() function", Verbosity::DEBUG);
                            retval = drs[i]->read_next_instance ( samples,
                                    sample_infos,
                                    LENGTH_UNLIMITED,
                                    previous_handles[i],
                                    ANY_SAMPLE_STATE,
                                    ANY_VIEW_STATE,
                                    ANY_INSTANCE_STATE );
                        } else {
                            logger.log_message("Calling read() function", Verbosity::DEBUG);
                            retval = drs[i]->read ( samples,
                                    sample_infos,
                                    LENGTH_UNLIMITED,
                                    ANY_SAMPLE_STATE,
                                    ANY_VIEW_STATE,
                                    ANY_INSTANCE_STATE );
                        }
#elif defined(TWINOAKS_COREDX)
                        if (options->take_read_next_instance) {
                            logger.log_message("Calling read_next_instance() function", Verbosity::DEBUG);
                            retval = drs[i]->read_next_instance ( &samples,
                                    &sample_infos,
                                    LENGTH_UNLIMITED,
                                    previous_handles[i],
                                    ANY_SAMPLE_STATE,
                                    ANY_VIEW_STATE,
                                    ANY_INSTANCE_STATE );
                        } else {
                            logger.log_message("Calling read() function", Verbosity::DEBUG);
                            retval = drs[i]->read_next_instance ( &samples,
                                    &sample_infos,
                                    LENGTH_UNLIMITED,
                                    ANY_SAMPLE_STATE,
                                    ANY_VIEW_STATE,
                                    ANY_INSTANCE_STATE );
                        }
#endif
                    }

                    if (retval == RETCODE_OK) {
                        auto n_samples = samples.length();
                        logger.log_message("Read " + std::to_string(n_samples)
                                + " sample(s), printing them...", Verbosity::DEBUG);
                        for (decltype(n_samples) n_sample = 0; n_sample < n_samples; n_sample++)  {
                            logger.log_message("Processing sample " + std::to_string(n_sample),
                                    Verbosity::DEBUG);
#if   defined(RTI_CONNEXT_DDS)
                            ShapeType          *sample      = &samples[n_sample];
                            SampleInfo         *sample_info = &sample_infos[n_sample];
#elif defined(TWINOAKS_COREDX)
                            ShapeType          *sample      = samples[n_sample];
                            SampleInfo         *sample_info = sample_infos[n_sample];
#elif defined(EPROSIMA_FAST_DDS) || defined(OPENDDS) || defined(INTERCOM_DDS)
                            const ShapeType    *sample      = &samples[n_sample];
                            SampleInfo         *sample_info = &sample_infos[n_sample];
#endif
                            if (sample_info->valid_data)  {
                                printf("%-10s %-10s %03d %03d [%d]", drs[i]->get_topicdescription()->get_name() NAME_ACCESSOR,
                                        sample->color FIELD_ACCESSOR STRING_IN,
                                        sample->x FIELD_ACCESSOR,
                                        sample->y FIELD_ACCESSOR,
                                        sample->shapesize FIELD_ACCESSOR );
                                if (DDS_UInt8Seq_get_length(&sample->additional_payload_size FIELD_ACCESSOR) > 0) {
                                    int additional_payload_index = DDS_UInt8Seq_get_length(&sample->additional_payload_size FIELD_ACCESSOR) - 1;
                                    printf(" {%u}", sample->additional_payload_size FIELD_ACCESSOR [additional_payload_index]);  
                                }
                                printf("\n");
#if defined(EPROSIMA_FAST_DDS)
                                instance_handle_color[sample_info->instance_handle] = sample->color FIELD_ACCESSOR STRING_IN;
#endif
                            } else {
                                ShapeType shape_key;
                                shape_initialize_w_color(shape_key, NULL);
#if defined(EPROSIMA_FAST_DDS)
                                shape_key.color FIELD_ACCESSOR = instance_handle_color[sample_info->instance_handle] NAME_ACCESSOR;
#else
                                drs[i]->get_key_value(shape_key, sample_info->instance_handle);
#endif
                                if (sample_info->instance_state == NOT_ALIVE_NO_WRITERS_INSTANCE_STATE) {
                                    printf("%-10s %-10s NOT_ALIVE_NO_WRITERS_INSTANCE_STATE\n",
                                            drs[i]->get_topicdescription()->get_name() NAME_ACCESSOR,
                                            shape_key.color FIELD_ACCESSOR STRING_IN);
                                } else if (sample_info->instance_state == NOT_ALIVE_DISPOSED_INSTANCE_STATE) {
                                    printf("%-10s %-10s NOT_ALIVE_DISPOSED_INSTANCE_STATE\n",
                                            drs[i]->get_topicdescription()->get_name() NAME_ACCESSOR,
                                            shape_key.color FIELD_ACCESSOR STRING_IN);
                                }
                            }
                        }

#if   defined(RTI_CONNEXT_DDS) || defined(OPENDDS) || defined(EPROSIMA_FAST_DDS) || defined(INTERCOM_DDS)
                        previous_handles[i] = sample_infos[0].instance_handle;
                        drs[i]->return_loan( samples, sample_infos );
#elif defined(TWINOAKS_COREDX)
                        previous_handles[i] = sample_infos[0]->instance_handle;
                        drs[i]->return_loan( &samples, &sample_infos );
#endif
                    }
                } while (retval == RETCODE_OK);
            }

            if (options->coherent_set_enabled || options->ordered_access_enabled) {
                sub->end_access();
            }

            // increasing number of iterations
            n++;
            logger.log_message("Subscriber iteration: <" + std::to_string(n) + ">", Verbosity::DEBUG);
            logger.log_message("Max number of iterations <" + std::to_string(options->num_iterations) + ">",
                    Verbosity::DEBUG);
            if (options->num_iterations != 0 && options->num_iterations <= n) {
                all_done = 1;
            }

            usleep(options->read_period_us);
        }

        free(previous_handles);

        return true;
    }

    //-------------------------------------------------------------
    void
    moveShape(ShapeType *shape)
    {
        shape->x FIELD_ACCESSOR = shape->x FIELD_ACCESSOR + xvel;
        shape->y FIELD_ACCESSOR = shape->y FIELD_ACCESSOR + yvel;
        if (shape->x FIELD_ACCESSOR < 0) {
            shape->x FIELD_ACCESSOR = 0;
            xvel = -xvel;
        }
        if (shape->x FIELD_ACCESSOR > da_width) {
            shape->x FIELD_ACCESSOR = da_width;
            xvel = -xvel;
        }
        if (shape->y FIELD_ACCESSOR < 0) {
            shape->y FIELD_ACCESSOR = 0;
            yvel = -yvel;
        }
        if (shape->y FIELD_ACCESSOR > da_height) {
            shape->y FIELD_ACCESSOR = da_height;
            yvel = -yvel;
        }
    }

    //-------------------------------------------------------------
    bool run_publisher(ShapeOptions *options)
    {
        logger.log_message("Running run_publisher() function", Verbosity::DEBUG);
        ShapeType shape;
        // number of iterations performed
        unsigned int n = 0;

        shape_initialize_w_color(shape, color);

        srandom((uint32_t)time(NULL));

        shape.shapesize FIELD_ACCESSOR = options->shapesize;
        shape.x FIELD_ACCESSOR =  random() % da_width;
        shape.y FIELD_ACCESSOR =  random() % da_height;
        xvel                   =  ((random() % 5) + 1) * ((random()%2)?-1:1);
        yvel                   =  ((random() % 5) + 1) * ((random()%2)?-1:1);

#if   defined(RTI_CONNEXT_DDS)
        if (options->additional_payload_size > 0) {
            int size = options->additional_payload_size;
            DDS_UInt8Seq_ensure_length(&shape.additional_payload_size FIELD_ACCESSOR, size, size);
            *DDS_UInt8Seq_get_reference(&shape.additional_payload_size FIELD_ACCESSOR, size - 1) = 255;
        } else {
            DDS_UInt8Seq_ensure_length(&shape.additional_payload_size FIELD_ACCESSOR, 0, 0);
        }
#else
        printf("DDS_UInt8Seq_ensure_length: Not supported\n");
#endif
        while ( ! all_done ) {
            moveShape(&shape);

            if (options->shapesize == 0) {
                shape.shapesize FIELD_ACCESSOR += 1;
            }

            if (options->coherent_set_enabled || options->ordered_access_enabled) {
                // n also represents the number of samples written per publisher per instance
                if (options->coherent_set_sample_count != 0 && n % options->coherent_set_sample_count == 0) {
                    printf("Started Coherent Set\n");
                    pub->begin_coherent_changes();
                }
            }

            for (unsigned int i = 0; i < options->num_topics; ++i) {
                for (unsigned int j = 0; j < options->num_instances; ++j) {
                    // Publish different instances with the same content (except for the color)
                    if (options->num_instances > 1) {
                        std::string instance_color = options->color + (j > 0 ? std::to_string(j) : "");
                        shape_set_color(shape, instance_color.c_str());
                    }

#if   defined(RTI_CONNEXT_DDS) || defined(OPENDDS) || defined(INTERCOM_DDS)
                    dws[i]->write( shape, HANDLE_NIL );
#elif defined(TWINOAKS_COREDX) || defined(EPROSIMA_FAST_DDS)
                    dws[i]->write( &shape, HANDLE_NIL );
#endif

                    if (options->print_writer_samples) {
                        printf("%-10s %-10s %03d %03d [%d]", dws[i]->get_topic()->get_name() NAME_ACCESSOR,
                                                shape.color FIELD_ACCESSOR STRING_IN,
                                                shape.x FIELD_ACCESSOR,
                                                shape.y FIELD_ACCESSOR,
                                                shape.shapesize FIELD_ACCESSOR);
                        if (options->additional_payload_size > 0) {
                            int additional_payload_index = options->additional_payload_size - 1;
                            printf(" {%u}", shape.additional_payload_size FIELD_ACCESSOR [additional_payload_index]);
                        }
                        printf("\n");
                    }
                }
            }

            if (options->coherent_set_enabled || options->ordered_access_enabled) {
                // n also represents the number of samples written per publisher per instance
                if (options->coherent_set_sample_count != 0
                        && n % options->coherent_set_sample_count == options->coherent_set_sample_count - 1) {
                    printf("Finished Coherent Set\n");
                    pub->end_coherent_changes();
                }
            }
            usleep(options->write_period_us);

            // increase number of iterations
            n++;

            logger.log_message("Publisher iteration: <" + std::to_string(n) + ">", Verbosity::DEBUG);
            logger.log_message("Max number of iterations <" + std::to_string(options->num_iterations) + ">",
                    Verbosity::DEBUG);

            if (options->num_iterations != 0 && options->num_iterations <= n) {
                all_done = 1;
            }
        }

        // Unregister or dispose instances of all DataWriters
        if (options->dispose || options->unregister) {
            for (unsigned int i = 0; i < options->num_topics; ++i) {
                for (unsigned int j = 0; j < options->num_instances; ++j) {
                    // Get instances
                    if (options->num_instances > 1) {
                        std::string instance_color = options->color + (j > 0 ? std::to_string(j) : "");
                        shape_set_color(shape, instance_color.c_str());
                    }
                    if (options->unregister) {
#if   defined(EPROSIMA_FAST_DDS)
                        dws[i]->unregister_instance(&shape, HANDLE_NIL);
#else
                        dws[i]->unregister_instance(shape, HANDLE_NIL);
#endif
                    }
                    if (options->dispose) {
#if   defined(EPROSIMA_FAST_DDS)
                        dws[i]->dispose(&shape, HANDLE_NIL);
#else
                        dws[i]->dispose(shape, HANDLE_NIL);
#endif
                    }
                }
            }
        }

        return true;
    }
};

/*************************************************************/
int main( int argc, char * argv[] )
{
    install_sig_handlers();

    ShapeOptions options;
    logger.log_message("Parsing command line parameters...", Verbosity::DEBUG);
    bool parseResult = options.parse(argc, argv);
    if ( !parseResult ) {
        exit(ERROR_PARSING_ARGUMENTS);
    }
    logger.log_message("Initializing ShapeApp...", Verbosity::DEBUG);
    ShapeApplication shapeApp;
    if ( !shapeApp.initialize(&options) ) {
        exit(ERROR_INITIALIZING);
    }
    logger.log_message("Running ShapeApp...", Verbosity::DEBUG);
    if ( !shapeApp.run(&options) ) {
        exit(ERROR_RUNNING);
    }

    printf("Done.\n");

    return 0;
}
