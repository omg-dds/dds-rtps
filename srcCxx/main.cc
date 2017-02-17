/*************************************************************/
/*************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <ctype.h>
#include <signal.h>
#include <string.h>
#include <stdarg.h>

#include <dds/dds.hh>
#include "shape.hh"
#include "shapeTypeSupport.hh"
#include "shapeDataReader.hh"
#include "shapeDataWriter.hh"

/*************************************************************/
int                 all_done           = 0;

/* Global configuration items: */
DDS::DomainId_t                     domain_id          = 0;
DDS::ReliabilityQosPolicyKind       reliability_kind   = (DDS::ReliabilityQosPolicyKind)-1; /* means 'defined default' */
DDS::DurabilityQosPolicyKind        durability_kind    = DDS::VOLATILE_DURABILITY_QOS;
int                 ownership_strength = -1; /* means shared */
char              * topic_name         = NULL;
char              * color              = NULL;
int                 publish            = 0;
int                 subscribe          = 0;

int                 da_width  = 240;
int                 da_height = 270;

int                 xvel = 3;
int                 yvel = 3;

DDS::DomainParticipantFactory * dpf   = NULL;
DDS::DomainParticipant        * dp    = NULL;
DDS::Publisher                * pub   = NULL;
DDS::Subscriber               * sub   = NULL;
DDS::Topic                    * topic = NULL;
ShapeTypeDataReader           * dr    = NULL;
ShapeTypeDataWriter           * dw    = NULL;

/***********************************************************************
 */
  class DPListener : public DomainParticipantListener 
  {
  public:
    void on_inconsistent_topic         ( Topic    *    topic,  const InconsistentTopicStatus & status){
      const char * topic_name = topic->get_name();
      const char * type_name  = topic->get_type_name();
      printf("%s() topic: '%s'  type: '%s'\n", __FUNCTION__, topic_name, type_name);
    }
    void on_offered_incompatible_qos(DataWriter *dw,  const OfferedIncompatibleQosStatus & status) { 
      Topic  * topic = dw->get_topic( );
      const char * topic_name = topic->get_name( );
      const char * type_name  = topic->get_type_name( );
      printf("%s() topic: '%s'  type: '%s' : %d\n", __FUNCTION__, topic_name, type_name, status.last_policy_id );
    }
    void on_requested_incompatible_qos ( DataReader *dr, const RequestedIncompatibleQosStatus & status){
      TopicDescription * topic      = dr->get_topicdescription( );
      const char       * topic_name = topic->get_name( );
      const char       * type_name  = topic->get_type_name( );
      printf("%s() topic: '%s'  type: '%s' : %d\n", __FUNCTION__, topic_name, type_name, status.last_policy_id );
    }
    
  };

DPListener dp_listener;

/*************************************************************/
void
print_usage( const char * prog )
{
  printf("%s: \n", prog);
  printf("   -d <int>        : domain id (default: 0)\n");
  printf("   -b              : BEST_EFFORT reliability\n");
  printf("   -r              : RELIABLE reliability\n");
  printf("   -s <int>        : set ownership strength [-1: SHARED]\n");
  printf("   -t <topic_name> : set the topic name\n");
  printf("   -c <color>      : set color to publish (filter if subscriber)\n");
  printf("   -D [v|t]        : set durability [v: VOLATILE, t: TRANSIENT_LOCAL]\n");
  printf("   -P              : publish samples\n");
  printf("   -S              : subscribe samples\n");
}

/*************************************************************/
int
parse_args(int argc, char * argv[])
{
  int opt;
  // double d;
  while ((opt = getopt(argc, argv, "hbc:d:D:rs:t:PS")) != -1) 
    {
      switch (opt) 
	{
        case 'b':
          reliability_kind = DDS::BEST_EFFORT_RELIABILITY_QOS;
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
                  durability_kind = DDS::VOLATILE_DURABILITY_QOS;
                  break;
                case 't':
                  durability_kind = DDS::TRANSIENT_LOCAL_DURABILITY_QOS;
                  break;
                default:
                  printf("unrecognized durability '%c'\n", optarg[0]);
                  break;
                }
            }
          break;
        case 'r':
          reliability_kind = DDS::RELIABLE_RELIABILITY_QOS;
          break;
        case 's':
          ownership_strength = atoi(optarg);
          break;
        case 't': 
          topic_name = strdup(optarg);
          break;
        case 'P':
          publish = 1;
          break;
        case 'S':
          subscribe = 1;
          break;
          
        case 'h':
          print_usage(argv[0]);
          exit(0);
          break;
        }
    }
  return 0;
}

/*************************************************************/
void
precondition( const char * prog, const char * str )
{
  print_usage(prog);
  printf("%s\n", str);
  exit(1);
}
/*************************************************************/
void
error( const char * fmt, ... )
{
  va_list    argptr;
  va_start(argptr, fmt);
  vprintf(fmt, argptr);
  va_end(argptr);
  exit(2);
}

/*************************************************************/
void 
handle_sig(int sig)
{
  if (sig == SIGINT)
    all_done = 1;
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
  sigaction(SIGUSR1, &int_action, NULL);
  return 0;
}

/*************************************************************/
void
moveShape( ShapeType * shape)
{
  int w2;
  
  w2 = 1 + shape->shapesize / 2;
  shape->x = shape->x + xvel;
  shape->y = shape->y + yvel;
  if (shape->x < w2)
    {
      shape->x = w2; 
      xvel = -xvel;
    }
  if (shape->x > da_width - w2)
    {
      shape->x = (da_width - w2);
      xvel = -xvel;
    }
  if (shape->y < w2)
    {
      shape->y = w2;
      yvel = -yvel;
    }
  if (shape->y > (da_height - w2) )
    {
      shape->y = (da_height - w2);
      yvel = -yvel;
    }
}

/*************************************************************/
int main( int argc, char * argv[] )
{
  /* set up defaults */
  install_sig_handlers();
  
  parse_args(argc, argv);

  if (color == NULL)
    color = strdup("BLUE");
  
  if (topic_name == NULL)
    precondition(argv[0], "please specify topic name [-t]");

  if ( (publish == 0) && (subscribe == 0) )
    precondition(argv[0], "please specify publish [-P] or subscribe [-S]");

  if ( publish && subscribe )
    precondition(argv[0], "please specify only one of: publish [-P] or subscribe [-S]");

  dpf = DDS::DomainParticipantFactory::get_instance();
  if (dpf == NULL)
    error("failed to create participant factory (missing license?).");
    
  dp = dpf->create_participant( domain_id, DDS::PARTICIPANT_QOS_DEFAULT, &dp_listener, DDS::ALL_STATUS );
  if (dp == NULL)
    error("failed to create participant (missing license?).");

  ShapeTypeTypeSupport::register_type(dp, "ShapeType");
  
  topic = dp->create_topic( topic_name, "ShapeType", DDS::TOPIC_QOS_DEFAULT, NULL, 0);
  if (topic == NULL)
    error("failed to create topic");
  
  if (publish)
    {
      DDS::DataWriterQos dw_qos;
      ShapeType          shape;

      topic = dp->create_topic( topic_name, "ShapeType", DDS::TOPIC_QOS_DEFAULT, NULL, 0);
      if (topic == NULL)
        error("failed to create topic");
      
      pub = dp->create_publisher(DDS::PUBLISHER_QOS_DEFAULT, NULL, 0);
      if (pub == NULL)
        error("failed to create publisher");

      pub->get_default_datawriter_qos( dw_qos );
      if ( reliability_kind  != -1 )
        dw_qos.reliability.kind = reliability_kind;
      if ( ownership_strength != -1 )
        {
          dw_qos.ownership.kind = DDS::EXCLUSIVE_OWNERSHIP_QOS;
          dw_qos.ownership_strength.value = ownership_strength;
        }
      
      dw = (ShapeTypeDataWriter *)pub->create_datawriter( topic, dw_qos, NULL, 0);

      if (dw == NULL)
        error("failed to create datawriter");

      srandom((uint32_t)time(NULL));
      strcpy(shape.color, color);
      shape.shapesize = 20;
      shape.x    =  random() % da_width;
      shape.y    =  random() % da_height;
      xvel       =  ((random() % 5) + 1) * ((random()%2)?-1:1);
      yvel       =  ((random() % 5) + 1) * ((random()%2)?-1:1);;
      
      while ( ! all_done )
        {
          moveShape(&shape);
          /* printf("write...\n"); */
          dw->write( &shape, DDS_HANDLE_NIL );
          
          usleep(33000);
        }
    }
  else if (subscribe)
    {
      DDS::DataReaderQos dr_qos;
      
      sub = dp->create_subscriber( DDS::SUBSCRIBER_QOS_DEFAULT, NULL, 0 );
      if (sub == NULL)
        error("failed to create subscriber");

      sub->get_default_datareader_qos( dr_qos );
      if ( reliability_kind  != -1 )
        dr_qos.reliability.kind = reliability_kind;
      if ( ownership_strength != -1 )
        dr_qos.ownership.kind = DDS::EXCLUSIVE_OWNERSHIP_QOS;
      dr_qos.durability.kind = durability_kind;

      if ( color != NULL ) /*  filter on specified color */
        {
          DDS::ContentFilteredTopic * cft;
          DDS::StringSeq              cf_params;
          cf_params.push_back( color );
          cft = dp->create_contentfilteredtopic( topic_name, topic, "color=%0", cf_params );
          if (cft == NULL)
            error("failed to create content filtered topic");
          dr = (ShapeTypeDataReader *)sub->create_datareader( cft, dr_qos, NULL, 0 );
        }
      else
        {
          dr = (ShapeTypeDataReader *)sub->create_datareader( topic, dr_qos, NULL, 0 );
        }
      
      if (dr == NULL)
        error("failed to create datareader");

      while ( ! all_done )
        {
          DDS::ReturnCode_t     retval;
          DDS::SampleInfoSeq    sample_infos;
          ShapeTypePtrSeq       samples;
          DDS::InstanceHandle_t previous_handle = DDS_HANDLE_NIL;
          
          do {
            retval = dr->take_next_instance ( &samples, 
                                              &sample_infos,
                                              DDS::LENGTH_UNLIMITED,
                                              previous_handle,
                                              DDS::ANY_SAMPLE_STATE,
                                              DDS::ANY_VIEW_STATE,
                                              DDS::ANY_INSTANCE_STATE );
            if (retval == DDS_RETCODE_OK)
              {
                int i;
                for (i = samples.length()-1; i>=0; i--)
                  {
                    if (sample_infos[i]->valid_data)
                      {
                        printf("%-10s %-10s %03d %03d [%d]\n", topic_name,
                               samples[i]->color,
                               samples[i]->x, 
                               samples[i]->y, 
                               samples[i]->shapesize );
                        break;
                      }
                  }
                previous_handle = sample_infos[0]->instance_handle;
                dr->return_loan( &samples, &sample_infos );
              }
          } while (retval == DDS::RETCODE_OK);
          
          usleep(100000);
        }
    }

  dp->delete_contained_entities( );
  dpf->delete_participant( dp );

  free(topic_name);
  free(color);
  
  return 0;
}
