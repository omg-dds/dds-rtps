
#include <dds/dds.hh>
#include "shape.hh"
#include "shapeTypeSupport.hh"
#include "shapeDataReader.hh"
#include "shapeDataWriter.hh"

#define CONFIGURE_PARTICIPANT_FACTORY      config_type_lookup();
#define LISTENER_STATUS_MASK_ALL           (ALL_STATUS)

#define DDS_UInt8Seq_get_length            DDS_seq_get_length
#define DDS_UInt8Seq_ensure_length(s,l,x)  do {  (s)->reserve(l); (s)->size(l); } while(0)
#define DDS_UInt8Seq_get_reference(s,l)    &( (*s)[l] )
#define Duration_from_micros(usec)         Duration_t( usec / USEC_PER_SEC, ( usec % USEC_PER_SEC ) * 1000 )

#define DDS_BOOLEAN_TRUE                   (1)
#define DDS_BOOLEAN_FALSE                  (0)

void StringSeq_push(DDS::StringSeq  &string_seq, const char *elem)
{
  char * e = NULL;
  if ( elem )
    {
      e = new char[strlen(elem)+1];
      if ( e )
        {
          strcpy( e, elem );
          string_seq.push_back(e);
        }
    }
}

const char *get_qos_policy_name(DDS_QosPolicyId_t policy_id)
{
  return DDS_qos_policy_str(policy_id);
}

static void config_type_lookup()
{
  /* turn off Type Lookup Service (not the focus of the test)
   */
  setenv( "COREDX_DO_TLS", "0", 1 );
}
