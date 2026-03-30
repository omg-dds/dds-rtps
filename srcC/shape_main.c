#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <getopt.h>
#include <stdbool.h>
#include <unistd.h>
#include "shape_configurator_cyclone_dds.h"
#include <stddef.h>
#include <string.h>
#include <time.h>
#include <signal.h>
#include <math.h>
#include <inttypes.h>

const size_t default_buffer_size = 256;
#define MAX_SAMPLES 500
#define ERROR_PARSING_ARGUMENTS 1
#define ERROR_INITIALIZING 2
#define ERROR_RUNNING 3

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

typedef enum {
    ERROR = 1,
    DEBUG = 2,
} Verbosity;


const char* to_string_reliability(dds_reliability_kind_t reliability_value)
{
    if (reliability_value == DDS_RELIABILITY_BEST_EFFORT){
        return "BEST_EFFORT";
    } else if (reliability_value == DDS_RELIABILITY_RELIABLE){
        return "RELIABLE";
    }
    return "Error stringifying Reliability kind.";
}
    
const char* to_string_durability(dds_durability_kind_t durability_value)
{
    if ( durability_value == DDS_DURABILITY_VOLATILE){
        return "VOLATILE";
    } else if (durability_value == DDS_DURABILITY_TRANSIENT_LOCAL){
        return "TRANSIENT_LOCAL";
    } else if (durability_value == DDS_DURABILITY_TRANSIENT){
        return "TRANSIENT";
    } else if (durability_value == DDS_DURABILITY_PERSISTENT){
        return "PERSISTENT";
    }
    return "Error stringifying Durability kind.";
}
    
const char* to_string_data_representation(dds_data_representation_id_t data_representation_value)
{
    if (data_representation_value == DDS_DATA_REPRESENTATION_XCDR1){
        return "XCDR";
    } else if (data_representation_value == DDS_DATA_REPRESENTATION_XCDR2){
        return "XCDR2";
    }
    return "Error stringifying DataRepresentation.";
}
    
const char* to_string_verbosity(Verbosity verbosity_value)
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
    
const char* to_string_ownership(dds_ownership_kind_t ownership_kind_value)
{
    if (ownership_kind_value == DDS_OWNERSHIP_SHARED){
        return "SHARED";
    } else if (ownership_kind_value == DDS_OWNERSHIP_EXCLUSIVE){
        return "EXCLUSIVE";
    }
    return "Error stringifying Ownership kind.";
}
    
const char* to_string_history(dds_history_kind_t history_kind_value)
{
    if (history_kind_value == DDS_HISTORY_KEEP_ALL){
        return "KEEP_ALL";
    } else if (history_kind_value == DDS_HISTORY_KEEP_LAST){
        return "KEEP_LAST";
    }
    return "Error stringifying History kind.";
}

const char* to_string_presentation(dds_presentation_access_scope_kind_t presentation_value)
{
    if (presentation_value == DDS_PRESENTATION_INSTANCE){
        return "INSTANCE_PRESENTATION_QOS";
    } else if (presentation_value == DDS_PRESENTATION_TOPIC){
        return "TOPIC_PRESENTATION_QOS";
    } else if (presentation_value == DDS_PRESENTATION_GROUP){
        return "GROUP_PRESENTATION_QOS";
    }
    return "error stringifying Access Scope kind";
}

    
typedef struct {
    Verbosity verbosity_;
} Logger;
    
Verbosity get_verbosity(Logger* logger)
{
    return logger->verbosity_;
}
    
void set_verbosity(Logger* logger, Verbosity v)
{
    logger->verbosity_ = v;
    return;
}
    
void log_message(Logger* logger, Verbosity level_verbosity, const char* format, ...)
{
    if (level_verbosity <= logger->verbosity_) {
        va_list arglist;
        va_start(arglist, format);
        vprintf(format, arglist);
        va_end(arglist);
        printf("\n");
    }
}

typedef struct ShapeOptions {
    dds_domainid_t                              domain_id;
    dds_reliability_kind_t                      reliability_kind;
    dds_durability_kind_t                       durability_kind;
    dds_data_representation_id_t                data_representation;
    int                                         history_depth;
    int                                         ownership_strength;
    dds_presentation_access_scope_kind_t        coherent_set_access_scope;

    char               *topic_name;
    char               *color;
    char               *partition;

    bool                publish;
    bool                subscribe;

    useconds_t          timebasedfilter_interval_us;
    useconds_t          deadline_interval_us;
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

    useconds_t          periodic_announcement_period_us;

    unsigned int        datafrag_size;
    char*               cft_expression;
    int                 size_modulo;
} ShapeOptions_t;


void shape_options_init(ShapeOptions_t* shape_options)
{
    shape_options->domain_id           = 0;
    shape_options->reliability_kind    = DDS_RELIABILITY_RELIABLE;
    shape_options->durability_kind     = DDS_DURABILITY_VOLATILE;
    shape_options->data_representation = DDS_DATA_REPRESENTATION_XCDR1;
    shape_options->history_depth       = -1;      /* means default */
    shape_options->ownership_strength  = -1;      /* means shared */

    shape_options->topic_name         = NULL;
    shape_options->color              = NULL;
    shape_options->partition          = NULL;

    shape_options->publish            = false;
    shape_options->subscribe          = false;

    shape_options->timebasedfilter_interval_us = 0; /* off */
    shape_options->deadline_interval_us        = 0; /* off */
    shape_options->lifespan_us                 = 0; /* off */

    shape_options->da_width  = 240;
    shape_options->da_height = 270;

    shape_options->xvel = 3;
    shape_options->yvel = 3;
    shape_options->shapesize = 20;

    shape_options->print_writer_samples = false;

    shape_options->use_read = false;

    shape_options->write_period_us = 33000; /* 33ms */
    shape_options->read_period_us = 100000; /* 100ms */

    shape_options->num_iterations = 0;
    shape_options->num_instances = 1;
    shape_options->num_topics = 1;

    shape_options->unregister = false;
    shape_options->dispose = false;
    
    shape_options->coherent_set_enabled = false;
    shape_options->ordered_access_enabled = false;
    shape_options->coherent_set_access_scope_set = false;
    shape_options->coherent_set_access_scope = DDS_PRESENTATION_INSTANCE;
    shape_options->coherent_set_sample_count = 0;

    shape_options->additional_payload_size = 0;

    shape_options->take_read_next_instance = true;

    shape_options->periodic_announcement_period_us = 0;

    shape_options->datafrag_size = 0; // Default: 0 (means not set)
    shape_options->cft_expression = NULL;

    shape_options->size_modulo = 0; // 0 means disabled

    return;
}

void shape_options_free(ShapeOptions_t* shape_options){
    free(shape_options->topic_name);
    free(shape_options->color);
    free(shape_options->partition);
    free(shape_options->cft_expression);
    return;
}

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
    printf("   -f <interval>   : set a 'deadline' with interval (ms) [0: OFF]\n");
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
    printf("   --time-filter <interval> : apply 'time based filter' with interval \n");
    printf("                              in ms [0: OFF]\n");
    printf("   --lifespan <int>      : indicates the lifespan of a sample in ms\n");
    printf("   --num-iterations <int>: indicates the number of iterations of the main loop\n");
    printf("                           After that, the application will exit.\n");
    printf("                           Default: infinite\n");
    printf("   --num-instances <int>: indicates the number of iterations of the main loop\n");
    printf("                          if the value is > 1, the additional instances are\n");
    printf("                          created by appending a number. For example, if the\n");
    printf("                          original color is \"BLUE\" the instances used are\n");
    printf("                          \"BLUE\", \"BLUE1\", \"BLUE2\"...\n");
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
    printf("   --coherent-sample-count <int>: amount of samples sent for each DataWriter\n");
    printf("                                  and instance that are grouped in a coherent\n");
    printf("                                  set\n");
    printf("   --additional-payload-size <bytes>: indicates the amount of bytes added to\n");
    printf("                                      the samples written (for example to use\n");
    printf("                                      large data)\n");
    printf("   --take-read           : uses take()/read() instead of take_next_instance()\n");
    printf("                           read_next_instance()\n");
    printf("   --periodic-announcement <ms> : indicates the periodic participant\n");
    printf("                                  announcement period in ms. Default 0 (off)\n");
    printf("   --datafrag-size <bytes> : set the data fragment size (default: 0, means\n");
    printf("                           not set)\n");
    printf("   --cft <expression> : ContentFilteredTopic filter expression (quotes\n");
    printf("                       required around the expression). Cannot be used with\n");
    printf("                        -c on subscriber applications\n");
    printf("   --size-modulo <int> : If set, the modulo operation is applied to the\n");
    printf("                         shapesize. This will make that shapesize is in the\n");
    printf("                         range [1,N]. This only applies if shapesize is\n");
    printf("                         increased (-z 0)\n");
}

bool validate(Logger* logger, ShapeOptions_t* shape_options) {
    if (shape_options->topic_name == NULL) {
        log_message(logger, ERROR, "please specify topic name [-t]");
        return false;
    }
    if ( (!shape_options->publish) && (!shape_options->subscribe) ) {
        log_message(logger, ERROR, "please specify publish [-P] or subscribe [-S]");
        return false;
    }
    if ( shape_options->publish && shape_options->subscribe ) {
        log_message(logger, ERROR, "please specify only one of: publish [-P] or subscribe [-S]");
        return false;
    }
    if (shape_options->publish && (shape_options->color == NULL) ) {
        shape_options->color = strdup("BLUE");
        log_message(logger, ERROR, "warning: color was not specified, defaulting to \"BLUE\"");
    }
    if (shape_options->publish && (shape_options->timebasedfilter_interval_us > 0)){
        log_message(logger, ERROR, "warning: time base filter [--time-filter] ignored on publisher applications");
    }
    if (shape_options->publish && shape_options->use_read) {
        log_message(logger, ERROR, "warning: use read [-R] ignored on publisher applications");
    }
    if (shape_options->publish && (!shape_options->take_read_next_instance)) {
        log_message(logger, ERROR, "warning: --take-read ignored on publisher applications");
    }
    if (shape_options->publish && shape_options->cft_expression != NULL) {
        log_message(logger, ERROR, "warning: --cft ignored on publisher applications");
    }
    if (shape_options->subscribe && (shape_options->shapesize != 20)){
        log_message(logger, ERROR, "warning: shapesize [-z] ignored on subscriber applications");
    }
    if (shape_options->subscribe && (shape_options->lifespan_us > 0)) {
        log_message(logger, ERROR, "warning: --lifespan ignored on subscriber applications");
    }
    if (shape_options->subscribe && (shape_options->num_instances > 1)) {
        log_message(logger, ERROR, "warning: --num-instances ignored on subscriber applications");
    }
    if (shape_options->subscribe && (shape_options->unregister || shape_options->dispose)) {
        log_message(logger, ERROR, "warning: --final-instance-state ignored on subscriber applications");
    }
    if (shape_options->subscribe && (shape_options->coherent_set_sample_count > 0)) {
        log_message(logger, ERROR, "warning: --coherent-sample-count ignored on subscriber applications");
    }
    if (!shape_options->coherent_set_enabled && !shape_options->ordered_access_enabled && shape_options->coherent_set_access_scope_set) {
        log_message(logger, ERROR, "warning: --access-scope ignored because not coherent, or ordered access enabled");
    }
    if (shape_options->size_modulo > 0 && shape_options->shapesize != 0) {
        log_message(logger, ERROR, "warning: --size-modulo has no effect unless shapesize (-z) is set to 0");
    }
    if (shape_options->subscribe && shape_options->color != NULL && shape_options->cft_expression != NULL) {
        log_message(logger, ERROR, "error: cannot specify both --cft and -c for subscriber applications");
        return false;
    }

    return true;
}


bool parse(int argc, char *argv[], Logger* logger, ShapeOptions_t* shape_options)
{
    log_message(logger, DEBUG, "Running parse() function");
    int opt;
    bool parse_ok = true;
    static struct option long_options[] = {
        {"help", no_argument, NULL, 'h'},
        {"write-period", required_argument, NULL, 'W'},
        {"read-period", required_argument, NULL, 'A'},
        {"final-instance-state", required_argument, NULL, 'M'},
        {"access-scope", required_argument, NULL, 'C'},
        {"coherent", required_argument, NULL, 'T'},
        {"ordered", required_argument, NULL, 'O'},
        {"coherent-sample-count", required_argument, NULL, 'H'},
        {"additional-payload-size", required_argument, NULL, 'B'},
        {"num-topics", required_argument, NULL, 'E'},
        {"lifespan", required_argument, NULL, 'l'},
        {"num-instances", required_argument, NULL, 'I'},
        {"num-iterations", required_argument, NULL, 'n'},
        {"take-read", required_argument, NULL, 'K'},
        {"time-filter", required_argument, NULL, 'i'},
        {"periodic-announcement", required_argument, NULL, 'N'},
        {"datafrag-size", required_argument, NULL, 'Z'},
        {"cft", required_argument, NULL, 'F'},
        {"size-modulo", required_argument, NULL, 'Q'},
        {NULL, 0, NULL, 0 }
    };

    // this variable will be used to check input values
    // because a lot of things are stored as unsigned ints
    // and cannot be checked for negative values
    int input_int = 0;

    while ((opt = getopt_long(argc, argv, "hPSbrRwc:d:D:f:k:p:s:x:t:v:z:",
            long_options, NULL)) != -1) {
        switch (opt) {
        case 'v':
            if (optarg[0] != '\0') {
                switch (optarg[0]) {
                case 'd':
                    set_verbosity(logger, DEBUG);
                    break;
                case 'e':
                    set_verbosity(logger, ERROR);
                    break;
                default:
                    log_message(logger, ERROR, "unrecognized value for verbosity %s", &optarg[0]);
                    parse_ok = false;
                }
            }
            break;
        case 'w':
            shape_options->print_writer_samples = true;
            break;
        case 'b':
            shape_options->reliability_kind = DDS_RELIABILITY_BEST_EFFORT;
            break;
        case 'R':
            shape_options->use_read = true;
            break;
        case 'c':
            shape_options->color = strdup(optarg);
            break;
        case 'd': {
            int converted_param = sscanf(optarg, "%d", &input_int);
            if (converted_param == 0) {
                log_message(logger, ERROR, "unrecognized value for domain_id %s", &optarg[0]);
                parse_ok = false;
            } else if (input_int < 0) {
                log_message(logger, ERROR, "incorrect value for domain_id (less than zero)");
                parse_ok = false;
            }
            shape_options->domain_id = (unsigned int)input_int;
            break;
        }
        case 'D':
        if (optarg[0] != '\0') {
            switch (optarg[0]) {
            case 'v':
                shape_options->durability_kind = DDS_DURABILITY_VOLATILE;
                break;
            case 'l':
                shape_options->durability_kind = DDS_DURABILITY_TRANSIENT_LOCAL;
                break;
            case 't':
                shape_options->durability_kind = DDS_DURABILITY_TRANSIENT;
                break;
            case 'p':
                shape_options->durability_kind = DDS_DURABILITY_PERSISTENT;
                break;
            default:
                log_message(logger, ERROR, "unrecognized value for durability %s", &optarg[0]);
                    parse_ok = false;
            }
        }
        break;
        case 'i': {
            int64_t time_input = 0;
            int converted_param = sscanf(optarg, "%lld", &time_input);
            if (converted_param == 0) {
                log_message(logger, ERROR, "unrecognized value for timebasedfilter_interval %s", &optarg[0]);
                parse_ok = false;
            } else if (time_input < 0) {
                log_message(logger, ERROR, "incorrect value for timebasedfilter_interval (less than zero)");
                parse_ok = false;
            }
            shape_options->timebasedfilter_interval_us = time_input * 1000ll;
            break;
        }
        case 'f': {
            int64_t time_input = 0;
            int converted_param = sscanf(optarg, "%lld", &time_input);
            if (converted_param == 0) {
                log_message(logger, ERROR, "unrecognized value for deadline_interval %s", &optarg[0]);
                parse_ok = false;
            } else if (time_input < 0) {
                log_message(logger, ERROR, "incorrect value for deadline_interval (less than zero)");
                parse_ok = false;
            }
            shape_options->deadline_interval_us = time_input * 1000ll;
            break;
        }
        case 'k': {
            int converted_param = sscanf(optarg, "%d", &input_int);
            if (converted_param == 0){
                log_message(logger, ERROR, "unrecognized value for history_depth %s", &optarg[0]);
                parse_ok = false;
            } else if (input_int < 0) {
                log_message(logger, ERROR, "incorrect value for history_depth (less than zero)");
                parse_ok = false;
            }
            shape_options->history_depth = (unsigned int)input_int;
            break;
        }
        case 'p':
            shape_options->partition = strdup(optarg);
            break;
        case 'r':
            shape_options->reliability_kind = DDS_RELIABILITY_RELIABLE;
            break;
        case 's': {
            int converted_param = sscanf(optarg, "%d", &input_int);
            if (converted_param == 0){
                log_message(logger, ERROR, "unrecognized value for ownership_strength %s", &optarg[0]);
                parse_ok = false;
            } else if (input_int < -1) {
                log_message(logger, ERROR, "incorrect value for ownership_strength (less than -1)");
                parse_ok = false;
            }
            shape_options->ownership_strength = (unsigned int)input_int;
            break;
        }
        case 't':
            shape_options->topic_name = strdup(optarg);
            break;
        case 'P':
            shape_options->publish = true;
            break;
        case 'S':
            shape_options->subscribe = true;
            break;
        case 'h':
            print_usage(argv[0]);
            exit(0);
            break;
        case 'x':
            if (optarg[0] != '\0') {
                switch (optarg[0]) {
                case '1':
                    shape_options->data_representation = DDS_DATA_REPRESENTATION_XCDR1;
                    break;
                case '2':
                    shape_options->data_representation = DDS_DATA_REPRESENTATION_XCDR2;
                    break;
                default:
                    log_message(logger, ERROR, "unrecognized value for data representation %s", &optarg[0]);
                    parse_ok = false;
                }
            }
            break;
        case 'z': {
            int converted_param = sscanf(optarg, "%d", &input_int);
            if (converted_param == 0) {
                log_message(logger, ERROR, "unrecognized value for shapesize %s", &optarg[0]);
                parse_ok = false;
            } else if (input_int < 0) {
                log_message(logger, ERROR, "incorrect value for shapesize (less than zero)");
                parse_ok = false;
            }
            shape_options->shapesize = (unsigned int)input_int;
            break;
        }
        case 'W': {
            dds_duration_t converted_param = 0;
            if (sscanf(optarg, "%lld", &converted_param) == 0) {
                log_message(logger, ERROR, "unrecognized value for write-period %s", &optarg[0]);
                parse_ok = false;
            } else if (converted_param < 0) {
                log_message(logger, ERROR, "incorrect value for write-period (less than zero)");
                parse_ok = false;
            }
            shape_options->write_period_us = converted_param * 1000ll;
            break;
        }
        case 'A': {
            dds_duration_t converted_param = 0;
            if (sscanf(optarg, "%lld", &converted_param) == 0) {
                log_message(logger, ERROR, "unrecognized value for read-period %s", &optarg[0]);
                parse_ok = false;
            } else if (converted_param < 0) {
                log_message(logger, ERROR, "incorrect value for read-period (less than zero)");
                parse_ok = false;
            }
            shape_options->read_period_us = converted_param * 1000ll;
            break;
        }
        case 'n': {
            if (sscanf(optarg, "%u", &shape_options->num_iterations) == 0) {
                log_message(logger, ERROR, "unrecognized value for num-iterations %s", &optarg[0]);
                parse_ok = false;
            } else if (shape_options->num_iterations < 1) {
                log_message(logger, ERROR, "incorrect value for num-iterations, it must be >= 1");
                parse_ok = false;
            }
            break;
        }
        case 'l': {
            dds_duration_t converted_param = 0;
            if (sscanf(optarg, "%lld", &converted_param) == 0) {
                log_message(logger, ERROR, "unrecognized value for lifespan %s", &optarg[0]);
                parse_ok = false;
            } else if (converted_param < 0) {
                log_message(logger, ERROR, "incorrect value for lifespan (less than zero)");
                parse_ok = false;
            }
            shape_options->lifespan_us = converted_param * 1000ll;
            break;
        }
        case 'M': {
            if (optarg[0] != '\0') {
                switch (optarg[0])
                {
                case 'u':
                    shape_options->unregister = true;
                    break;
                case 'd':
                    shape_options->dispose = true;
                default:
                    log_message(logger, ERROR, "unrecognized value for final-instance-state %s", &optarg[0]);
                    parse_ok = false;
                }
                if (shape_options->unregister && shape_options->dispose){
                    log_message(logger, ERROR, "error, cannot confiture unregister and dispose at the same time");
                    parse_ok = false;
                }
            }
            break;
        }
        case 'C': {
            shape_options->coherent_set_access_scope_set = true;
            if (optarg[0] != '\0') {
                switch (optarg[0])
                {
                case 'i':
                    shape_options->coherent_set_access_scope = DDS_PRESENTATION_INSTANCE;
                    break;
                case 't':
                    shape_options->coherent_set_access_scope = DDS_PRESENTATION_TOPIC;
                    break;
                case 'g':
                    shape_options->coherent_set_access_scope = DDS_PRESENTATION_GROUP;
                    break;
                default:
                    log_message(logger, ERROR, "unrecognized value for cogerent-sets %s", &optarg[0]);
                    parse_ok = false;
                    shape_options->coherent_set_access_scope_set = false;
                }
            }
            break;
        }
        case 'T': {
            shape_options->coherent_set_enabled = true;
            break;
        }
        case 'O': {
            shape_options->ordered_access_enabled = true;
            break;
        }
        case 'I': {
            if (sscanf(optarg, "%u", &shape_options->num_instances) == 0) {
                log_message(logger, ERROR, "unrecognized value for num-instances %s", &optarg[0]);
                parse_ok = false;
            } else if (shape_options->num_instances < 1) {
                log_message(logger, ERROR, "incorrect value for num-instances, it must be >= 1");
                parse_ok = false;
            }
            break;
        }
        case 'E': {
            if (sscanf(optarg, "%u", &shape_options->num_topics) == 0) {
                log_message(logger, ERROR, "unrecognized value for num-topics %s", &optarg[0]);
                parse_ok = false;
            } else if (shape_options->num_topics < 1) {
                log_message(logger, ERROR, "incorrect value for num-topics, it must be >= 1");
                parse_ok = false;
            }
            break;
        }
        case 'B': {
            if (sscanf(optarg, "%u", &shape_options->additional_payload_size) == 0) {
                log_message(logger, ERROR, "unrecognized value for additional-payload-size %s", &optarg[0]);
                parse_ok = false;
            } else if (shape_options->additional_payload_size < 1) {
                log_message(logger, ERROR, "incorrect value for additional-payload-size, it must be >= 1");
                parse_ok = false;
            }
            break;
        }
        case 'H': {
            if (sscanf(optarg, "%u", &shape_options->coherent_set_sample_count) == 0) {
                log_message(logger, ERROR, "unrecognized value for coherent-sample-count %s", &optarg[0]);
                parse_ok = false;
            } else if (shape_options->coherent_set_sample_count < 2) {
                log_message(logger, ERROR, "incorrecct value for coherent-sample-ount, it must be >= 2");
                parse_ok = false;
            }
            break;
        }
        case 'K': {
            shape_options->take_read_next_instance = false;
            break;
        }
        case 'N': {
            dds_duration_t converted_param = 0;
            if (sscanf(optarg, "%lld", &converted_param) == 0){
                log_message(logger, ERROR, "unrecognized value for periodic-announcement %s", &optarg[0]);
                parse_ok = false;
            } else if (converted_param < 0) {
                log_message(logger, ERROR, "incorrect value for periodic-announcement, it must be >= 0");
                parse_ok = false;
            }
            shape_options->periodic_announcement_period_us = converted_param * 1000ll;
            break;
        }
        case 'Z': {
            unsigned int converted_param = 0;
            if (sscanf(optarg, "%u", &converted_param) == 0) {
                log_message(logger, ERROR, "unrecognized value for datafrag-size %c", optarg[0]);
                parse_ok = false;
            }
            // the spec mentions that the fragment size must satisfy:
            // fragment size <= 65535 bytes.
            if (converted_param > 65535) {
                log_message(logger, ERROR, "incorrect value for datafrag-size, "
                        "it must be <= 65535 bytes%u", converted_param);
                parse_ok = false;
            }
            shape_options->datafrag_size = converted_param;
            break;
        }
        case 'F':
            shape_options->cft_expression = strdup(optarg);
            break;
        case 'Q': {
            int converted_param = 0;
            if (sscanf(optarg, "%d", &converted_param) == 0 || converted_param < 1) {
                log_message(logger, ERROR, "incorrect value for size-modulo, must be >=1");
                parse_ok = false;
            } else {
                shape_options->size_modulo = converted_param;
            }
            break;
        }
        case '?':
            parse_ok = false;
            break;
        }
    }

    if ( parse_ok ) {
        parse_ok = validate(logger, shape_options);
    }
    if ( !parse_ok ) {
        print_usage(argv[0]);
        exit(1);
    } else if (DEBUG <= logger->verbosity_){
        printf("Shape Options: \n");
        printf("    Verbosity = %d\n", get_verbosity(logger));
        printf("    This application %s a publisher\n", shape_options->publish ? "is" : "is not");
        printf("    This application %s a subscriber\n", shape_options->subscribe ? "is" : "is not");
        printf("    DomainId = %d\n", shape_options->domain_id);
        printf("    ReliabilityKind = %d\n", shape_options->reliability_kind);
        printf("    DurabilityKind = %d\n", shape_options->durability_kind);
        printf("    DataRepresentation = %d\n", shape_options->data_representation);
        printf("    HistoryDepth = %d\n", shape_options->history_depth);
        printf("    OwnershipStrength = %d\n",shape_options->ownership_strength);
        printf("    TimeBasedFilterInterval = %u ms\n",shape_options->timebasedfilter_interval_us / 1000ll);
        printf("    DeadlineInterval = %u ms\n", shape_options->deadline_interval_us / 1000ll);
        printf("    Shapesize = %d\n", shape_options->shapesize);
        printf("    Reading method = %s\n", (shape_options->use_read 
                     ? (shape_options->take_read_next_instance ? "read_next_instance" : "read") 
                     : (shape_options->take_read_next_instance ? "take_next_instance" : "take")));
        printf("    Write period = %u ms\n", shape_options->write_period_us / 1000ll);
        printf("    Read period = %u ms\n", shape_options->read_period_us / 1000ll);
        printf("    Lifespan = %u ms\n", shape_options->lifespan_us / 1000ll);
        printf("    Number of iterations = %u\n", shape_options->num_iterations);
        printf("    Number of instances = %u\n", shape_options->num_instances);
        printf("    Number of entities = %u\n", shape_options->num_topics);
        printf("    Coherent sets = %s\n", shape_options->coherent_set_enabled ? "true" : "false");
        printf("    Ordered access  = %s\n", shape_options->ordered_access_enabled ? "true" : "false");
        printf("    Access Scope  = %s\n", to_string_presentation(shape_options->coherent_set_access_scope));
        printf("    Coherent Sample Count = %u\n", shape_options->coherent_set_sample_count);
        printf("    Additional Payload Size = %u\n", shape_options->additional_payload_size);
        printf("    Final Instance State = %s\n", 
                     (shape_options->unregister ? "Unregister" : (shape_options->dispose ? "Dispose" : "not specified")));
        printf("    Periodic Announcement Period = %u ms\n", shape_options->periodic_announcement_period_us / 1000ll);
        printf("    Data Fragmentation Size = %u bytes\n", shape_options->datafrag_size);
        if (shape_options->topic_name != NULL){
            printf("    Topic = %s\n", shape_options->topic_name);
        }
        if (shape_options->color != NULL) {
            printf("    Color = %s\n", shape_options->color);
        }
        if (shape_options->partition != NULL) {
            printf("    Partition = %s\n", shape_options->partition);
        }
    }
    return parse_ok;
}

typedef struct ShapeApp {
    Logger* logger;

    dds_listener_t* dp_listner;
    dds_entity_t dp;
    dds_entity_t* topics;
    dds_entity_t publisher;
    dds_entity_t subscriber;
   
    dds_entity_t* writers;
    dds_entity_t* readers;

    char* color;

    int xval;
    int yval;
    int da_width;
    int da_hight;
} ShapeApp_t;

void on_inconsistent_topic(dds_entity_t topic,  const dds_inconsistent_topic_status_t status, void* args) {
    Logger* logger = args;    

    char topic_name[default_buffer_size];
    char type_name[default_buffer_size];
    
    if (dds_get_name(topic, topic_name, default_buffer_size) < 0) {
        log_message(logger, ERROR, "Failed to get topic name for topic %d in %s", topic, __FUNCTION__);

        exit(-1);
    }

    if (dds_get_type_name(topic, type_name, default_buffer_size) < 0){
        log_message(logger, ERROR, "Failed to get type name for topic: %s in %s", topic_name, __FUNCTION__);

        exit(-1);
    }

    printf("%s() topic: '%s'  type: '%s'\n", __FUNCTION__, topic_name, type_name);
}

void on_offered_incompatible_qos(dds_entity_t writer, const dds_offered_incompatible_qos_status_t status, void * args) {
    dds_entity_t topic = dds_get_topic(writer);
    Logger* logger = args;
    
    char topic_name[default_buffer_size];
    char type_name[default_buffer_size];
    const char* policy_name = get_qos_policy_name(status.last_policy_id);

    if (policy_name == NULL) {
        log_message(logger, ERROR, "Failed to get qos Policy name for policy id: %u in %s", status.last_policy_id, __FUNCTION__);
        exit(-1);
    }
    
    if (dds_get_name(topic, topic_name, default_buffer_size) < 0) {
        log_message(logger, ERROR, "Failed to get topic name for topic %d in %s",topic,__FUNCTION__);

        exit(-1);
    }

    if (dds_get_type_name(topic, type_name, default_buffer_size) < 0){
        log_message(logger, ERROR, "Failed to get type name for topic: %s in %s",topic_name,__FUNCTION__);

        exit(-1);
    }


    printf("%s() topic: '%s'  type: '%s' : %d (%s)\n", __FUNCTION__,
            topic_name, type_name,
            status.last_policy_id,
            policy_name );
}

void on_publication_matched (dds_entity_t writer, const dds_publication_matched_status_t status, void* args) {
    dds_entity_t topic = dds_get_topic(writer);
    Logger* logger = args;
 
    char topic_name[default_buffer_size];
    char type_name[default_buffer_size];

    if (dds_get_name(topic, topic_name, default_buffer_size) < 0) {
        log_message(logger, ERROR, "Failed to get topic name for topic %d in %s",topic,__FUNCTION__);

        exit(-1);
    }

    if (dds_get_type_name(topic, type_name, default_buffer_size) < 0){
        log_message(logger, ERROR, "Failed to get type name for topic: %s in %s",topic_name,__FUNCTION__);

        exit(-1);
    }

    printf("%s() topic: '%s'  type: '%s' : matched readers %d (change = %d)\n", __FUNCTION__,
            topic_name, type_name, status.current_count, status.current_count_change);
}

void on_offered_deadline_missed (dds_entity_t writer, const dds_offered_deadline_missed_status_t status, void* args) {
    dds_entity_t topic = dds_get_topic(writer);
    Logger* logger = args;

    char topic_name[default_buffer_size];    
    char type_name[default_buffer_size];

    if (dds_get_name(topic, topic_name, default_buffer_size) < 0) {
        log_message(logger, ERROR, "Failed to get topic name for topic %d in %s",topic,__FUNCTION__);

        exit(-1);
    }

    if (dds_get_type_name(topic, type_name, default_buffer_size) < 0){
        log_message(logger, ERROR, "Failed to get type name for topic: %s in %s",topic_name,__FUNCTION__);

        exit(-1);
    }

    printf("%s() topic: '%s'  type: '%s' : (total = %d, change = %d)\n", __FUNCTION__,
            topic_name, type_name, status.total_count, status.total_count_change);
}

void on_liveliness_lost (dds_entity_t writer, const dds_liveliness_lost_status_t status, void * args) {
    dds_entity_t topic = dds_get_topic(writer);
    Logger* logger = args;
    
    char topic_name[default_buffer_size];
    char type_name[default_buffer_size];

    if (dds_get_name(topic, topic_name, default_buffer_size) < 0) {
        log_message(logger, ERROR, "Failed to get topic name for topic %d in %s",topic,__FUNCTION__);

        exit(-1);
    }

    if (dds_get_type_name(topic, type_name, default_buffer_size) < 0){
        log_message(logger, ERROR, "Failed to get type name for topic: %s in %s",topic_name,__FUNCTION__);

        exit(-1);
    }

    printf("%s() topic: '%s'  type: '%s' : (total = %d, change = %d)\n", __FUNCTION__,
            topic_name, type_name, status.total_count, status.total_count_change);
}

void on_requested_incompatible_qos (dds_entity_t reader, const dds_requested_incompatible_qos_status_t status, void * args) {
    dds_entity_t topic = dds_get_topic(reader); 
    Logger* logger = args;
    
    char topic_name[default_buffer_size];
    char type_name[default_buffer_size];

    if (dds_get_name(topic, topic_name, default_buffer_size) < 0) {
        log_message(logger, ERROR,"Failed to get topic name for topic %d in %s",topic,__FUNCTION__);

        exit(-1);
    }

    if (dds_get_type_name(topic, type_name, default_buffer_size) < 0){
        log_message(logger, ERROR, "Failed to get type name for topic: %s in %s",topic_name,__FUNCTION__);

        exit(-1);
    }

    const char *policy_name = get_qos_policy_name(status.last_policy_id);

    if (policy_name == NULL) {
        log_message(logger, ERROR, "Failed to get qos Policy name for policy id: % in %s", status.last_policy_id, __FUNCTION__);

        exit(-1);
    }

    printf("%s() topic: '%s'  type: '%s' : %d (%s)\n", __FUNCTION__,
            topic_name, type_name, status.last_policy_id,
            policy_name);
}

void on_subscription_matched (dds_entity_t reader, const dds_subscription_matched_status_t status, void* args) {
    dds_entity_t topic = dds_get_topic(reader);
    Logger* logger = args;

    char topic_name[default_buffer_size];
    char type_name[default_buffer_size];

    if (dds_get_name(topic, topic_name, default_buffer_size) < 0) {
        log_message(logger, ERROR,"Failed to get topic name for topic %d in %s",topic,__FUNCTION__);

        exit(-1);
    }

    if (dds_get_type_name(topic, type_name, default_buffer_size) < 0){
        log_message(logger, ERROR, "Failed to get type name for topic: %s in %s",topic_name,__FUNCTION__);

        exit(-1);
    }

    printf("%s() topic: '%s'  type: '%s' : matched writers %d (change = %d)\n", __FUNCTION__,
            topic_name, type_name, status.current_count, status.current_count_change);
}

void on_requested_deadline_missed (dds_entity_t reader, const dds_requested_deadline_missed_status_t status, void* args) {
    dds_entity_t topic = dds_get_topic(reader);
    Logger* logger = args;
    
    char topic_name[default_buffer_size];
    char type_name[default_buffer_size];
    
    if (dds_get_name(topic, topic_name, default_buffer_size) < 0) {
        log_message(logger, ERROR,"Failed to get topic name for topic %d in %s",topic,__FUNCTION__);

        exit(-1);
    }

    if (dds_get_type_name(topic, type_name, default_buffer_size) < 0){
        log_message(logger, ERROR, "Failed to get type name for topic: %s in %s",topic_name,__FUNCTION__);

        exit(-1);
    }

    printf("%s() topic: '%s'  type: '%s' : (total = %d, change = %d)\n", __FUNCTION__,
            topic_name, type_name, status.total_count, status.total_count_change);
}

void on_liveliness_changed (dds_entity_t reader, const dds_liveliness_changed_status_t status, void* args) {
    dds_entity_t topic = dds_get_topic(reader);
    Logger* logger = args;
    
    char topic_name[default_buffer_size];
    char type_name[default_buffer_size];

    if (dds_get_name(topic, topic_name, default_buffer_size) < 0) {
        log_message(logger, ERROR,"Failed to get topic name for topic %d in %s",topic,__FUNCTION__);

        exit(-1);
    }

    if (dds_get_type_name(topic, type_name, default_buffer_size) < 0){
        log_message(logger, ERROR, "Failed to get type name for topic: %s in %s",topic_name,__FUNCTION__);

        exit(-1);
    }

    printf("%s() topic: '%s'  type: '%s' : (alive = %d, not_alive = %d)\n", __FUNCTION__,
            topic_name, type_name, status.alive_count, status.not_alive_count);
}

void on_sample_rejected (dds_entity_t e, const dds_sample_rejected_status_t status, void* data) {}
void on_data_available (dds_entity_t e, void* data) {}
void on_sample_lost (dds_entity_t e, const dds_sample_lost_status_t status, void* data) {}
void on_data_on_readers (dds_entity_t e, void* data) {}

void set_reliability(dds_qos_t* qos, dds_reliability_kind_t reliability_kind, Logger* logger) {
    dds_time_t duration;

    dds_qset_reliability(qos, reliability_kind, DDS_INFINITY);    
    if (!dds_qget_reliability(qos, &reliability_kind, &duration)) {
        log_message(logger, ERROR, "Failed to get reliability kind");
    }
    
    log_message(logger, DEBUG, "    Reliability = %s", to_string_reliability(reliability_kind));
}

void set_durability(dds_qos_t* qos, dds_durability_kind_t durability_kind, Logger* logger){
    dds_qset_durability(qos, durability_kind);    
    dds_qget_durability(qos, &durability_kind);
    
    log_message(logger, DEBUG,"    Durability = %s", to_string_durability(durability_kind));
}

void set_data_representation(dds_qos_t* qos, dds_data_representation_id_t data_representation, Logger* logger){
    uint32_t count = 1;
    dds_data_representation_id_t* data_representation_list;
    dds_qset_data_representation(qos, count, &data_representation);
    if (!dds_qget_data_representation(qos,&count, &data_representation_list)) {
        printf("Failed to get data representation"); 
    }
    
    log_message(logger, DEBUG, "    Data_Representation = %s", to_string_data_representation(*data_representation_list));
}

void set_ownership(dds_qos_t* qos, int ownership_strength, Logger* logger) {
    if (ownership_strength != -1) {
        dds_qset_ownership(qos, DDS_OWNERSHIP_EXCLUSIVE);
        dds_qset_ownership_strength(qos, ownership_strength);
    } else {
        dds_qset_ownership(qos, DDS_OWNERSHIP_SHARED);
    }
    
    dds_ownership_kind_t ownership_kind;
    dds_qget_ownership(qos, &ownership_kind);
    
    log_message(logger,DEBUG,"    Ownership = %s", to_string_ownership(ownership_kind));
    
    if(ownership_kind == DDS_OWNERSHIP_EXCLUSIVE) {
        dds_qget_ownership_strength(qos, &ownership_strength);
        
        log_message(logger, DEBUG, "    OwnershptStrength = %d", ownership_strength);
    }
}

void set_deadline_interval(dds_qos_t* qos, dds_time_t deadline_interval, Logger* logger) {
    dds_time_t duration;

    if (deadline_interval > 0) {
        dds_qset_deadline(qos, deadline_interval);
    }

    dds_qget_deadline(qos, &duration);

    log_message(logger, DEBUG,"    DeadlinePeriod = %lld nanosecs", duration);
}

void set_history_depth(dds_qos_t* qos, int history_depth, Logger* logger){
    if (history_depth < 0) {
        dds_qset_history(qos, DDS_HISTORY_KEEP_LAST, 1);
	dds_qset_durability_service(qos, 0, DDS_HISTORY_KEEP_LAST, 1, DDS_LENGTH_UNLIMITED, DDS_LENGTH_UNLIMITED, DDS_LENGTH_UNLIMITED);
    } else if (history_depth > 0) {
        dds_qset_history(qos, DDS_HISTORY_KEEP_LAST, history_depth);
	dds_qset_durability_service(qos, 0, DDS_HISTORY_KEEP_LAST, history_depth, DDS_LENGTH_UNLIMITED, DDS_LENGTH_UNLIMITED, DDS_LENGTH_UNLIMITED);
    } else {
        dds_qset_history(qos, DDS_HISTORY_KEEP_ALL, 0);
	dds_qset_durability_service(qos, 0, DDS_HISTORY_KEEP_ALL, 0, DDS_LENGTH_UNLIMITED, DDS_LENGTH_UNLIMITED, DDS_LENGTH_UNLIMITED);
    }

    dds_history_kind_t history;
    dds_qget_history(qos,&history,&history_depth);

    log_message(logger, DEBUG, "    History = %s", to_string_history(history));
    
    if (history == DDS_HISTORY_KEEP_LAST) {
        log_message(logger, DEBUG,"    HistoryDepth = %d", history_depth);
    }
}

void set_time_based_filter(dds_qos_t* qos, dds_duration_t timebasedfilter_interval, Logger* logger) {
    dds_duration_t duration;

    if(timebasedfilter_interval >= 0 ) {
        dds_qset_time_based_filter(qos, timebasedfilter_interval);
    }

    dds_qget_time_based_filter(qos, &duration );
    log_message(logger,DEBUG, "    TimeBasedFilter = %lld nanosecs", duration);
}

void set_presentation(dds_qos_t* qos, dds_presentation_access_scope_kind_t coherent_set_access_scope, bool coherent_set_enabled, bool ordered_access_enabled, Logger* logger) {
    dds_qset_presentation(qos, coherent_set_access_scope, coherent_set_enabled, ordered_access_enabled);

    dds_presentation_access_scope_kind_t access_scope;
    bool coherent_access;
    bool ordered_access;
    dds_qget_presentation(qos, &access_scope, &coherent_access, &ordered_access);
    log_message(logger, DEBUG, "    Presentation Coherent Access = %s", coherent_access ? "true" : "false");
    log_message(logger, DEBUG, "    Presentation Ordered Access = %s", ordered_access ? "true" : "false");
    log_message(logger, DEBUG, "    Presentation Access Scope = %s", to_string_presentation(access_scope));
}

void set_lifespan(dds_qos_t* qos, dds_duration_t lifespan, Logger* logger) {
    if (lifespan > 0) {
        dds_qset_lifespan(qos, lifespan);
    }
    dds_duration_t lfspn;
    dds_qget_lifespan(qos, &lfspn);

    log_message(logger, DEBUG, "    Lifespan = %lld nanosecs", lfspn);
}

void set_writer_data_lifecycle(dds_qos_t* qos, bool autodispose, Logger* logger){
    dds_qset_writer_data_lifecycle(qos, !autodispose);

    bool atdsp;
    dds_qget_writer_data_lifecycle(qos, &atdsp);
    log_message(logger, DEBUG, "    Autodispose_unregistered_instances = %s", atdsp ? "true" : "false");
}

bool init_publisher(const ShapeOptions_t* opts, ShapeApp_t* app) {
    log_message(app->logger, DEBUG, "Running init_publisher() function");

    dds_qos_t* dw_qos = dds_create_qos();
    dds_qos_t* pub_qos = dds_create_qos();

    if (opts->partition != NULL) {
        dds_qset_partition(pub_qos, 1,  &opts->partition);
    }

    log_message(app->logger, DEBUG, "Publisher QoS:");

    set_presentation(pub_qos, opts->coherent_set_access_scope, opts->coherent_set_enabled, opts->ordered_access_enabled, app->logger);

    app->publisher = dds_create_publisher(app->dp, pub_qos, NULL);
    
    if (app->publisher < 0) {
        log_message(app->logger, ERROR, "Failed to create publisher");

        return false;
    }
    
    log_message(app->logger, DEBUG, "Publisher created");
    log_message(app->logger, DEBUG, "Data Writer QoS:");

    set_reliability(dw_qos, opts->reliability_kind, app->logger);
    set_durability(dw_qos, opts->durability_kind, app->logger);
    set_data_representation(dw_qos,opts->data_representation, app->logger);
    set_ownership(dw_qos, opts->ownership_strength,app->logger);
    set_deadline_interval(dw_qos, opts->deadline_interval_us * 1000ll, app->logger);
    set_history_depth(dw_qos, opts->history_depth, app->logger);
    set_lifespan(dw_qos, opts->lifespan_us * 1000ll, app->logger);
    set_writer_data_lifecycle(dw_qos, opts->unregister, app->logger);

    for (unsigned int i = 0; i < opts->num_topics; ++i) {
        char temp;
        dds_return_t name_len = dds_get_name(app->topics[i], &temp, 1);
        if (name_len < 0) {
            log_message(app->logger, ERROR, "Failed to get name of topic");
            return false;
        }
        char* name = calloc(name_len + 1, sizeof(char));
        dds_get_name(app->topics[i], name, name_len + 1);
        printf("Create writer for topic: %s color: %s\n", name, opts->color); 
        app->writers[i] = dds_create_writer(app->publisher, app->topics[i], dw_qos, NULL);
        if (app->writers[i] < 0) {
            log_message(app->logger, ERROR, "failed to create datawriter[%u] topic: %s", i, name);
            free(name);
            return false;
        }
        free(name);
    }

    log_message(app->logger, DEBUG, "DataWriters created:");
    for (unsigned int i = 0; i < opts->num_topics; ++i) {
        log_message(app->logger, DEBUG, "    dws(%u)=%d", i, app->writers[i]);
    }

    app->color = strdup(opts->color);
    app->xval = opts->xvel;
    app->yval = opts->yvel;
    app->da_width = opts->da_width;
    app->da_hight = opts->da_height;

    return true;
}

bool color_filter(const void* sample, void* arg) {
    const char* color = arg;
    ShapeType const * const shape = sample;

    return strcmp(color,shape->color) == 0;
}

bool init_subscriber(const ShapeOptions_t* opts, ShapeApp_t* app) {

    log_message(app->logger, DEBUG,"Running init_subscriber() function");

    dds_qos_t* sub_qos = dds_create_qos();
    if (sub_qos == NULL) log_message(app->logger,ERROR,"Failed to create sub_qos");

    log_message(app->logger, DEBUG, "Subscriber QoS:");

    set_presentation(sub_qos, opts->coherent_set_access_scope, opts->coherent_set_enabled, opts->ordered_access_enabled, app->logger);

    dds_qos_t* dr_qos = dds_create_qos();
    if(sub_qos == NULL) log_message(app->logger, ERROR, "failed to create data reader qos.");

    if (opts->partition != NULL) {
        dds_qset_partition(sub_qos, 1, &opts->partition);
    }
   
    app->subscriber = dds_create_subscriber(app->dp, sub_qos, NULL);
    if (app->subscriber < 0 ) {
        log_message(app->logger, ERROR, "Failed to create subscriber");
        return false;
    }

    log_message(app->logger, DEBUG,"subscriber created");
    log_message(app->logger, DEBUG, "Data Reader QoS: ");
   
    set_reliability(dr_qos, opts->reliability_kind, app->logger);
    set_durability(dr_qos, opts->durability_kind, app->logger);
    set_data_representation(dr_qos, opts->data_representation, app->logger);
    set_ownership(dr_qos, opts->ownership_strength, app->logger);
    set_time_based_filter(dr_qos, opts->timebasedfilter_interval_us * 1000ll, app->logger);
    set_deadline_interval(dr_qos, opts->deadline_interval_us * 1000ll, app->logger);
    set_history_depth(dr_qos, opts->history_depth, app->logger);

    if (opts->cft_expression != NULL) {
        log_message(app->logger, ERROR, "ContectFilterTopic Not Supported");
        return false;
    }

    if (opts->cft_expression != NULL || opts->color != NULL) {
        for (unsigned int i = 0; i < opts->num_topics; ++i) {
            char temp;
            size_t name_len = dds_get_name(app->topics[i], &temp, 1);
            char* name = malloc(sizeof(char) * (name_len + 1));
            dds_get_name(app->topics[i], name, name_len + 1);

            if (dds_set_topic_filter_and_arg(app->topics[i],color_filter, app->color) >= 0 ) {
                log_message(app->logger, DEBUG, "    ContentFilterTopic = \"color = %s\"", opts->color);
            } else {
                log_message(app->logger, ERROR, "failed to create content filtered topic");
                return false;
            }

            printf("Create reader for topic: %s%s\n", name, "_filtered");
            app->readers[i] = dds_create_reader(app->subscriber, app->topics[i], dr_qos, NULL);
            if (app->readers[i] == 0) {
                log_message(app->logger, ERROR, "Failed to create datareader[%u] topic: %s", i, name);
                free(name);
                return false;
            }
            free(name);
        }
    } else {
        for (unsigned int i = 0; i < opts->num_topics; ++i) {
            char temp;
            size_t name_len = dds_get_name(app->topics[i], &temp, 1);
            char* name = malloc(sizeof(char) * (name_len + 1));
            dds_get_name(app->topics[i], name, name_len + 1);
            printf("Create reader for topic: %s\n", name);
            app->readers[i] = dds_create_reader(app->subscriber, app->topics[i], dr_qos, NULL);
            if (app->readers[i] == 0) {
                log_message(app->logger, ERROR, "failed to create datareader[%u] topic: %s", i, name);
                free(name);
                return false;
            }
            free(name);
        }
    }
    log_message(app->logger, DEBUG,"DataReaders created:");
    for (unsigned int i = 0; i < opts->num_topics; ++i) {
        log_message(app->logger, DEBUG, "    drs(%u)=%ld", i, app->readers[i]);
    }

    return true;
}


bool shape_init (ShapeApp_t* app,  const ShapeOptions_t* opts, Logger* logger) {
    
    app->logger = logger;
    app->publisher = 0;
    app->subscriber = 0;
    app->dp = 0;
    app->topics = NULL;
    app->readers = NULL;
    app->writers = NULL;
    app->dp_listner = dds_create_listener(logger);

    dds_lset_inconsistent_topic(app->dp_listner, on_inconsistent_topic);
    dds_lset_offered_incompatible_qos(app->dp_listner, on_offered_incompatible_qos);
    dds_lset_publication_matched(app->dp_listner, on_publication_matched);
    dds_lset_offered_deadline_missed(app->dp_listner, on_offered_deadline_missed);
    dds_lset_liveliness_lost(app->dp_listner, on_liveliness_lost);
    dds_lset_requested_incompatible_qos(app->dp_listner, on_requested_incompatible_qos);
    dds_lset_subscription_matched(app->dp_listner, on_subscription_matched);
    dds_lset_requested_deadline_missed(app->dp_listner, on_requested_deadline_missed);
    dds_lset_liveliness_changed(app->dp_listner, on_liveliness_changed);
    dds_lset_sample_rejected(app->dp_listner, on_sample_rejected);
    dds_lset_data_available(app->dp_listner, on_data_available);
    dds_lset_sample_lost(app->dp_listner,on_sample_lost);
    dds_lset_data_on_readers(app->dp_listner, on_data_on_readers);
 
    dds_qos_t* dp_qos = dds_create_qos();

    if (opts->datafrag_size > 0) {
        bool result = false;
        if (!result) {
            log_message(logger, ERROR, "Error configuring Data Fragmentation Size = %u", opts->datafrag_size);
            return false;
        } else {
            log_message(logger, DEBUG, "Data Fragmentation Size = %u", opts->datafrag_size);
        }
    }

    app->dp = dds_create_participant(opts->domain_id, dp_qos, app->dp_listner);

    if (app->dp < 0 ) {
        log_message(logger, ERROR, "failed to create participant (missing license?)." );

        return false;
    }

    dds_qos_t* topic_qos = dds_create_qos();
    
    set_history_depth(topic_qos,opts->history_depth, app->logger);
    dds_qset_resource_limits (topic_qos, MAX_SAMPLES, DDS_LENGTH_UNLIMITED, DDS_LENGTH_UNLIMITED);
    
    app->topics = (dds_entity_t*) malloc(sizeof(dds_entity_t) * opts->num_topics);
    if (app->topics == NULL) {
        log_message(logger, ERROR, "Error allocating memory for topics");
        return false;
    }
    for (unsigned int i = 0; i < opts->num_topics; ++i) {
        app->topics[i] = 0;
    }

    if (opts->publish) {
        app->writers = (dds_entity_t*) malloc(sizeof(dds_entity_t) * opts->num_topics);
        if (app->writers == NULL) {
            log_message(logger, ERROR, "Error allocating memory for DataWriters");
            return false;
        }
        for (unsigned int i = 0; i < opts->num_topics; ++i) {
            app->writers[i] = 0;
        }
    } else {
        app->readers = (dds_entity_t*) malloc(sizeof(dds_entity_t) * opts->num_topics);
        if (app->readers == NULL) {
            log_message(logger, ERROR, "Error allocating memory for DataReaders");
            return false;
        }
        for (unsigned int i = 0; i < opts->num_topics; ++i) {
            app->readers[i] = 0;
        }
    }

    for (unsigned int i = 0; i < opts->num_topics; ++i) {
        char* topic_name = calloc(((i > 0) ? (int)log10f(i) : 0) + strlen(opts->topic_name) + 2, sizeof(char));
        if (topic_name == NULL) {
            log_message(logger, ERROR, "Error allocating memory for Topic names");
            return false;
        }
        if (i > 0) {
            sprintf(topic_name, "%s%u", opts->topic_name, i);
        } else {
            sprintf(topic_name, "%s", opts->topic_name);
        }
        printf("Create topic: %s\n", topic_name);
        app->topics[i] = dds_create_topic(app->dp, &ShapeType_desc, topic_name, topic_qos, NULL);
        if (app->topics[i] < 0) {
            log_message(logger, ERROR, "failed to create topic <%s>", topic_name);
            free(topic_name);
            return false;
        }
        free(topic_name);
    }
    log_message(logger, DEBUG, "Topics created:");
    for (unsigned int i = 0; i < opts->num_topics; ++i) {
        log_message(logger, DEBUG, "    topic(%d)=%p", i, (void*)app->topics[i]);
    }

    if (opts->publish) {
        return init_publisher(opts, app);
    } else {
        return init_subscriber(opts,app);
    }
} 

bool run_subscriber(ShapeApp_t app, ShapeOptions_t opts) {
    // This is the number of iterations performed
    unsigned int n = 0;
    dds_instance_handle_t *previous_handles = NULL;

    log_message(app.logger, DEBUG, "Running run_subscriber() function");
    bool printed_message = false;

    previous_handles = (dds_instance_handle_t*) malloc(sizeof(dds_instance_handle_t) * opts.num_topics);
    if (previous_handles == NULL) {
        log_message(app.logger, ERROR, "Error allocating memory for previous_handles");
        return false;
    }
    for (int i = 0; i < opts.num_topics; ++i) {
        previous_handles[i] = 0;
    }
    
    while(!all_done) {
        dds_return_t retval;
        dds_sample_info_t sample_infos[MAX_SAMPLES];
        void* samples[MAX_SAMPLES];

        for( size_t i = 0; i < MAX_SAMPLES; i ++) samples[i] = ShapeType__alloc();
        if(opts.coherent_set_enabled) {
            printf("Reading coherent sets, iteration %u\n", n);
        }
        if(opts.ordered_access_enabled) {
            printf("Reading with ordered access, iteration %u\n", n);
        }
        if (opts.coherent_set_enabled || opts.ordered_access_enabled) {
            dds_begin_coherent(app.subscriber);
        }

        for (unsigned int i = 0; i < opts.num_topics; ++i) {
            previous_handles[i] = 0;
            do {
                if(!opts.use_read) {
                    if(opts.take_read_next_instance) {
                        if (!printed_message) {
                            printed_message = true;
                            log_message(app.logger, DEBUG, "Calling take_next_instance() function"); 
                        }
                        retval = dds_take_next_instance(app.readers[i], samples,sample_infos, MAX_SAMPLES, MAX_SAMPLES, previous_handles[i]);
                    } else {
                        if (!printed_message) {
                            printed_message = true;
                            log_message(app.logger, DEBUG, "Calling take() function");
                        }
                        retval = dds_take(app.readers[i], samples, sample_infos, MAX_SAMPLES, MAX_SAMPLES);
                    }
                } else {
                    if(opts.take_read_next_instance) {
                        if (!printed_message) {
                            printed_message = true;
                            log_message(app.logger, DEBUG, "Calling read_next_instance() function"); 
                        }
                        retval = dds_read_next_instance(app.readers[i], samples,sample_infos, MAX_SAMPLES, MAX_SAMPLES, previous_handles[i]);
                    } else {
                        if (!printed_message) {
                            printed_message = true;
                            log_message(app.logger, DEBUG, "Calling read() function");
                        }
                        retval = dds_read(app.readers[i], samples, sample_infos, MAX_SAMPLES, MAX_SAMPLES);
                    }
                }
                
                if (retval > DDS_RETCODE_OK) {
                    log_message(app.logger, DEBUG, "Read %d sample(s), printing them...",retval);
                    
                    for (size_t n_sample = 0; n_sample < retval; n_sample++) {
                        log_message(app.logger, DEBUG, "Processing sample %lu",n_sample);
    
                        ShapeType* sample = samples[n_sample];
                        dds_sample_info_t* sample_info = &sample_infos[n_sample];
    
                        if (sample_info->valid_data) {
                            char name[default_buffer_size];
                            
                            dds_entity_t topic = dds_get_topic(app.readers[i]);
                            dds_get_name(topic, name, default_buffer_size);
                            
                            printf("%-10s %-10s %03d %03d [%d]",name,sample->color,sample->x,sample->y,sample->shapesize);
                            if(sample->additional_payload_size._length > 0){
                                int additional_payload_index = sample->additional_payload_size._length - 1;
                                printf(" {%u}", sample->additional_payload_size._buffer[additional_payload_index]);
                            }
                            printf("\n");
                        }
                        if (sample_info->instance_state != DDS_IST_ALIVE) {
                            ShapeType shape_key;
                            dds_instance_get_key(app.readers[i], sample_info->instance_handle, &shape_key);
                            if (sample_info->instance_state == DDS_IST_NOT_ALIVE_NO_WRITERS) {
                                dds_entity_t reader_topic = dds_get_topic(app.readers[i]);
                                char temp;
                                dds_return_t name_len = dds_get_name(reader_topic, &temp, 1);
                                char* name = calloc(name_len + 1, sizeof(char));
                                dds_get_name(reader_topic, name, name_len + 1);
                                printf("%-10s %-10s NOT_ALIVE_NO_WRITERS_INSTANCE_STATE\n", name, shape_key.color);
                                free(name);
                            } else if (sample_info->instance_state == DDS_IST_NOT_ALIVE_DISPOSED) {
                                dds_entity_t reader_topic = dds_get_topic(app.readers[i]);
                                char temp;
                                dds_return_t name_len = dds_get_name(reader_topic, &temp, 1);
                                char* name = calloc(name_len + 1, sizeof(char));
                                dds_get_name(reader_topic, name, name_len + 1);
                                printf("%-10s %-10s NOT_ALIVE_DISPOSED_INSTANCE_STATE\n", name, shape_key.color);
                                free(name);
                            }
                        }
                    }
                    dds_return_loan(app.readers[i], (void**)samples, MAX_SAMPLES);
                    previous_handles[i] = sample_infos[0].instance_handle;
                } 
                log_message(app.logger, DEBUG, "retval: %d", retval);
            } while (retval > DDS_RETCODE_OK);
        }
        if (opts.coherent_set_enabled || opts.ordered_access_enabled) {
            dds_end_coherent(app.subscriber);
        }

        n++;
        log_message(app.logger, DEBUG, "Subscriber iteration: <%u>", n);
        log_message(app.logger, DEBUG, "Max number of iterations <%u>", opts.num_iterations);
        if (opts.num_iterations != 0 && opts.num_iterations <= n) {
            all_done = 1;
        }

        for( size_t i = 0; i < MAX_SAMPLES; i ++) ShapeType_free(samples[i],DDS_FREE_ALL);
        usleep(opts.read_period_us);
    }

    free(previous_handles);
    
    return true;
}

void moveShape(ShapeType *shape, ShapeApp_t* app) {
    shape->x = shape->x + app->xval;
    shape->y = shape->x + app->yval;

    if (shape->x < 0) {
        shape->x = 0;
        app->xval = -app->xval;
    }
    if (shape->x > app->da_width) {
        shape->x = app->da_width;
        app->xval = -app->xval;
    }
    if (shape->y < 0) {
        shape->y = 0;
        app->yval = -app->yval;
    }
    if (shape->y > app->da_hight) {
        shape->y = app->da_hight;
        app->yval = -app->yval;
    }
}

bool run_publisher(ShapeApp_t app, ShapeOptions_t opts) {
    log_message(app.logger, DEBUG, "Running run_publisher() function");
    ShapeType shape;
    // number of iterations performed
    unsigned int n = 0;

    srand((uint32_t)time(NULL));
    size_t index = 0;
    
    memcpy(shape.color, app.color, strlen(app.color));
    shape.color[strlen(app.color)] = '\0';
    
    shape.shapesize = opts.shapesize;
    shape.x = random() % app.da_width;
    shape.y = random() % app.da_hight;
    
    app.xval = ((random() % 5) + 1) * ((random() % 2)?-1:1);
    app.yval = ((random() % 5) + 1) * ((random() % 2)?-1:1);

    if (opts.additional_payload_size > 0) {
        int size = opts.additional_payload_size;
        shape.additional_payload_size._buffer = dds_sequence_uint8_allocbuf(size);
        shape.additional_payload_size._maximum = size;
        shape.additional_payload_size._length = size;
        for (int i = 0; i < size; ++i) {
            shape.additional_payload_size._buffer[i] = 255;
        }
    } else {
        shape.additional_payload_size._buffer = dds_sequence_uint8_allocbuf(0);
        shape.additional_payload_size._maximum = 0;
        shape.additional_payload_size._length = 0;
    }

    while(! all_done) {
        moveShape(&shape, &app);

        if (opts.shapesize == 0) {
            if (opts.size_modulo > 0) {
                shape.shapesize = (shape.shapesize % opts.size_modulo) + 1;
            } else {
                shape.shapesize += 1;
            }
        }

        if (opts.coherent_set_enabled || opts.ordered_access_enabled) {
            // n also represents the number of samples written per publisher per instance
            if (opts.coherent_set_sample_count != 0 && n % opts.coherent_set_sample_count == 0) {
                printf("Started Coherent Set\n");
                dds_begin_coherent(app.publisher);
            }
        }

        for (unsigned int i = 0; i < opts.num_topics; ++i) {
            for (unsigned int j = 0; j < opts.num_instances; ++j) {
                //Publish different instances with the same content (except for the color)
                if (opts.num_instances > 1) {
                    if (strlen(opts.color) > 0) {
                        sscanf(shape.color, "%s%u", opts.color, j);
                    } else {
                        sscanf(shape.color, "%s", opts.color);
                    }
                    if (opts.unregister) {
                        dds_unregister_instance(app.writers[i], &shape);
                    }
                    if (opts.dispose) {
                        dds_dispose(app.writers[i], &shape);
                    }
                }
                dds_return_t rc = dds_write(app.writers[i], &shape);
                if (opts.print_writer_samples) {
                    dds_entity_t writer_topic = dds_get_topic(app.writers[i]);
                    char temp;
                    dds_return_t name_len = dds_get_name(writer_topic, &temp, 1);
                    char* name = calloc(name_len + 1, sizeof(char));
		    dds_get_name(writer_topic, name, name_len + 1);
                    printf("%-10s %-10s %03d %03d [%d]", name,
                        shape.color,
                        shape.x,
                        shape.y,
                        shape.shapesize);
                    if (opts.additional_payload_size > 0) {
                        int additional_payload_index = opts.additional_payload_size - 1;
                        printf(" {%u}", shape.additional_payload_size._buffer[additional_payload_index]);
                    }
                    printf("\n");
                    free(name);
                }
            }
        }

        if (opts.coherent_set_enabled || opts.ordered_access_enabled) {
            if (opts.coherent_set_sample_count != 0 
                    && n % opts.coherent_set_sample_count == opts.coherent_set_sample_count - 1) {
                printf("Finished Coherent Set\n");
                dds_end_coherent(app.publisher);
            }
        }
        
        usleep(opts.write_period_us);

        n++;

        log_message(app.logger, DEBUG, "Publisher iteration: <%u>", n);
        log_message(app.logger, DEBUG, "Max number of iterations <%u>", opts.num_iterations);

        if (opts.num_iterations != 0 && opts.num_iterations <= n){
            all_done = 1;
        }
    }

    if (opts.dispose || opts.unregister) {
        for (unsigned int i = 0; i < opts.num_topics; ++i) {
            for (unsigned int j = 0; j < opts.num_instances; ++j) {
                if (opts.num_instances > 1) {
                    if (j > 0) {
                        sprintf(shape.color, "%s%u", opts.color, j);
                    } else {
                        sprintf(shape.color, "%s", opts.color);
                    }
                }
                if (opts.unregister) {
                    dds_unregister_instance(app.writers[i], &shape);
                }
                if (opts.dispose) {
                    dds_dispose(app.writers[i], &shape);
                }
            }
        }
    }

    for (unsigned int i = 0; i < opts.num_topics; ++i) {
        dds_wait_for_acks(app.writers[i], DDS_SECS(1));
    }

    return true;
}

bool run(ShapeApp_t app, ShapeOptions_t opts) {
    log_message(app.logger, DEBUG,"Running run() function");

    if (app.publisher != 0) {
        return run_publisher(app, opts);
    } else if (app.subscriber != 0) {
        return run_subscriber(app, opts); 
    }

    return false;
}

void shape_free(ShapeApp_t * app,const ShapeOptions_t *opts) {
    dds_delete(app->dp);
    dds_delete_listener(app->dp_listner);
}

int main(int argc,char **argv) 
{ 

    ShapeOptions_t opts;
    Logger logger;
    logger.verbosity_ = ERROR;

    shape_options_init(&opts);
    if (!parse(argc, argv, &logger, &opts)) {
        return ERROR_PARSING_ARGUMENTS; 
    }
    //set_verbosity(&logger, DEBUG);
    
    ShapeApp_t shape_app;
     
    if (!shape_init(&shape_app,&opts, &logger)) {
        return ERROR_INITIALIZING;
    }

    if (!run(shape_app, opts)) {
        return ERROR_RUNNING;
    }

    shape_free(&shape_app,&opts);

    return 0; 
}
