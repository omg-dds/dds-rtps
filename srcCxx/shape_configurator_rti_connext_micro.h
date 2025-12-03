#include "shape_micro.h"
#include "shape_microSupport.h"

#include "rti_me_cpp.hxx"
#include "dds_cpp/dds_cpp_netio.hxx"

#include <map>
#include <cstring>

#define CONFIGURE_PARTICIPANT_FACTORY config_micro();
#define LISTENER_STATUS_MASK_ALL (DDS_STATUS_MASK_ALL)

#ifndef XCDR_DATA_REPRESENTATION
  #define XCDR_DATA_REPRESENTATION DDS_XCDR_DATA_REPRESENTATION
#endif

#ifndef XCDR2_DATA_REPRESENTATION
  #define XCDR2_DATA_REPRESENTATION DDS_XCDR2_DATA_REPRESENTATION
#endif

#ifndef PresentationQosPolicyAccessScopeKind
    #define PresentationQosPolicyAccessScopeKind DDS_PresentationQosPolicyAccessScopeKind
#endif

#ifndef INSTANCE_PRESENTATION_QOS
    #define INSTANCE_PRESENTATION_QOS DDS_INSTANCE_PRESENTATION_QOS
#endif

#ifndef TOPIC_PRESENTATION_QOS
    #define TOPIC_PRESENTATION_QOS DDS_TOPIC_PRESENTATION_QOS
#endif

#ifndef GROUP_PRESENTATION_QOS
    #define GROUP_PRESENTATION_QOS DDS_GROUP_PRESENTATION_QOS
#endif


#define DataRepresentationId_t DDS_DataRepresentationId_t
#define DataRepresentationIdSeq DDS_DataRepresentationIdSeq

typedef CDR_StringSeq StringSeq;

const DDS::DurabilityQosPolicyKind TRANSIENT_DURABILITY_QOS = DDS_TRANSIENT_DURABILITY_QOS;
const DDS::DurabilityQosPolicyKind PERSISTENT_DURABILITY_QOS = DDS_PERSISTENT_DURABILITY_QOS;

void StringSeq_push(StringSeq  &string_seq, const char *elem)
{
    string_seq.ensure_length(string_seq.length()+1, string_seq.length()+1);
    string_seq[string_seq.length()-1] = DDS_String_dup(elem);
}


const char* get_qos_policy_name(DDS::QosPolicyId_t policy_id)
{
  //case DDS::USERDATA_QOS_POLICY_ID) { return "USERDATA";
  if (policy_id == DDS::DURABILITY_QOS_POLICY_ID) { return "DURABILITY"; }
  else if (policy_id == DDS::PRESENTATION_QOS_POLICY_ID) { return "PRESENTATION"; }
  else if (policy_id == DDS::DEADLINE_QOS_POLICY_ID) { return "DEADLINE"; }
  else if (policy_id == DDS::LATENCYBUDGET_QOS_POLICY_ID) { return "LATENCYBUDGET"; }
  else if (policy_id == DDS::OWNERSHIP_QOS_POLICY_ID) { return "OWNERSHIP"; }
  else if (policy_id == DDS::OWNERSHIPSTRENGTH_QOS_POLICY_ID) { return "OWNERSHIPSTRENGTH"; }
  else if (policy_id == DDS::LIVELINESS_QOS_POLICY_ID) { return "LIVELINESS"; }
  else if (policy_id == DDS::TIMEBASEDFILTER_QOS_POLICY_ID) { return "TIMEBASEDFILTER"; }
  else if (policy_id == DDS::PARTITION_QOS_POLICY_ID) { return "PARTITION"; }
  else if (policy_id == DDS::RELIABILITY_QOS_POLICY_ID) { return "RELIABILITY"; }
  else if (policy_id == DDS::DESTINATIONORDER_QOS_POLICY_ID) { return "DESTINATIONORDER"; }
  else if (policy_id == DDS::HISTORY_QOS_POLICY_ID) { return "HISTORY"; }
  else if (policy_id == DDS::RESOURCELIMITS_QOS_POLICY_ID) { return "RESOURCELIMITS"; }
  else if (policy_id == DDS::ENTITYFACTORY_QOS_POLICY_ID) { return "ENTITYFACTORY"; }
  else if (policy_id == DDS::WRITERDATALIFECYCLE_QOS_POLICY_ID) { return "WRITERDATALIFECYCLE"; }
  else if (policy_id == DDS::READERDATALIFECYCLE_QOS_POLICY_ID) { return "READERDATALIFECYCLE"; }
  else if (policy_id == DDS::TOPICDATA_QOS_POLICY_ID) { return "TOPICDATA"; }
  else if (policy_id == DDS::GROUPDATA_QOS_POLICY_ID) { return "GROUPDATA"; }
  else if (policy_id == DDS::TRANSPORTPRIORITY_QOS_POLICY_ID) { return "TRANSPORTPRIORITY"; }
  else if (policy_id == DDS::LIFESPAN_QOS_POLICY_ID) { return "LIFESPAN"; }
  else if (policy_id == DDS::DURABILITYSERVICE_QOS_POLICY_ID) { return "DURABILITYSERVICE"; }
  else { return "Unknown"; }
}

static void config_micro()
{
  RT::Registry *registry = NULL;

  OSAPI_Log_set_verbosity(OSAPI_LOG_VERBOSITY_SILENT);

  registry = DDSTheParticipantFactory->get_registry();

  /* Register Writer History */
  if (!registry->register_component("wh", WHSMHistoryFactory::get_interface(), NULL, NULL))
  {
      printf("ERROR: unable to register writer history\n");
      return;
  }

  /* Register Reader History */
  if (!registry->register_component("rh", RHSMHistoryFactory::get_interface(), NULL, NULL))
  {
    printf("ERROR: unable to register reader history\n");
    return;
  }

  /* Configure UDP transport's allowed interfaces */
  if (!registry->unregister(NETIO_DEFAULT_UDP_NAME, NULL, NULL))
  {
      printf("ERROR: unable to unregister udp\n");
      return;
  }

  UDP_InterfaceFactoryProperty *udp_property = new UDP_InterfaceFactoryProperty();
  if (udp_property == NULL)
  {
      printf("ERROR: unable to allocate udp properties\n");
      return;
  }

  /* For additional allowed interface(s), increase maximum and length, and
  set interface below:
  */
  if (!udp_property->allow_interface.maximum(1))
  {
      printf("ERROR: unable to set allow_interface maximum\n");
      return;
  }
  if (!udp_property->allow_interface.length(1))
  {
      printf("ERROR: unable to set allow_interface length\n");
      return;
  }

#if defined(RTI_LINUX)
    udp_property->allow_interface[0] = DDS_String_dup("lo");
    printf("Configured UDP to allow interface lo\n");
#elif defined(RTI_DARWIN)
    udp_property->allow_interface[0] = DDS_String_dup("lo0");
    printf("Configured UDP to allow interface lo0\n");
#endif
  //udp_property->allow_interface[1] = DDS_String_dup("eth0");

  if (!registry->register_component(
      NETIO_DEFAULT_UDP_NAME,
      UDPInterfaceFactory::get_interface(),
      &udp_property->_parent._parent,
      NULL))
  {
      printf("ERROR: unable to register udp\n");
      return;
  }

  DPDE::DiscoveryPluginProperty *discovery_plugin_properties = new DPDE::DiscoveryPluginProperty();

  /* Configure properties */
  discovery_plugin_properties->participant_liveliness_assert_period.sec = 5;
  discovery_plugin_properties->participant_liveliness_assert_period.nanosec = 0;
  discovery_plugin_properties->participant_liveliness_lease_duration.sec = 30;
  discovery_plugin_properties->participant_liveliness_lease_duration.nanosec = 0;


  if (!registry->register_component(
      "dpde",
      DPDEDiscoveryFactory::get_interface(),
      &discovery_plugin_properties->_parent,
      NULL))
  {
      printf("ERROR: unable to register dpde\n");
      return;
  }
}

static bool configure_dp_qos(DDS::DomainParticipantQos &dp_qos)
{
    if (!dp_qos.discovery.discovery.name.set_name("dpde"))
    {
        printf("ERROR: unable to set discovery plugin name\n");
        return false;
    }

    dp_qos.discovery.initial_peers.maximum(1);
    dp_qos.discovery.initial_peers.length(1);
    dp_qos.discovery.initial_peers[0] = DDS_String_dup("127.0.0.1");
    /* if there are more remote or local endpoints, you need to increase these limits */
    dp_qos.resource_limits.max_destination_ports = 32;
    dp_qos.resource_limits.max_receive_ports = 32;
    dp_qos.resource_limits.local_topic_allocation = 2;
    dp_qos.resource_limits.local_type_allocation = 2;
    //TODO we need to increase this
    dp_qos.resource_limits.local_reader_allocation = 2;
    dp_qos.resource_limits.local_writer_allocation = 2;
    dp_qos.resource_limits.remote_participant_allocation = 8;
    dp_qos.resource_limits.remote_reader_allocation = 8;
    dp_qos.resource_limits.remote_writer_allocation = 8;
    return true;
}

uint64_t DDS_UInt8Seq_get_length(DDS_OctetSeq * seq)
{
  return seq->length();
}

void DDS_UInt8Seq_ensure_length(DDS_OctetSeq * seq, uint64_t length, uint64_t max)
{
  seq->ensure_length(length, max);
}

unsigned char* DDS_UInt8Seq_get_reference(DDS_OctetSeq * seq, uint64_t index)
{
  return DDS_OctetSeq_get_reference(seq, index);
}

const unsigned char* DDS_UInt8Seq_get_reference(const DDS_OctetSeq * seq, uint64_t index)
{
  return DDS_OctetSeq_get_reference(seq, index);
}

struct InstanceHandle_t_less_op {
    bool operator()(const DDS::InstanceHandle_t& a, const DDS::InstanceHandle_t& b) const {
        return std::memcmp(a.octet, b.octet, 16);
    }
};
