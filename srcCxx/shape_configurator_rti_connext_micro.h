#include "shape_bounded.h"
#include "shape_boundedSupport.h"

#include "rti_me_cpp.hxx"
#include "dds_cpp/dds_cpp_netio.hxx"

#include <map>
#include <cstring>

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

static bool config_micro()
{
  bool ok = false;
  RT::Registry *registry = NULL;
  DPDE::DiscoveryPluginProperty *discovery_plugin_properties = NULL;
  UDP_InterfaceFactoryProperty *udp_property = NULL;

  OSAPI_Log_set_verbosity(OSAPI_LOG_VERBOSITY_SILENT);

  registry = DDSTheParticipantFactory->get_registry();

  /* Register Writer History */
  if (!registry->register_component("wh", WHSMHistoryFactory::get_interface(), NULL, NULL))
  {
      printf("ERROR: unable to register writer history\n");
      goto done;
  }

  /* Register Reader History */
  if (!registry->register_component("rh", RHSMHistoryFactory::get_interface(), NULL, NULL))
  {
      printf("ERROR: unable to register reader history\n");
      goto done;
  }

  /* Configure UDP transport's allowed interfaces */
  if (!registry->unregister(NETIO_DEFAULT_UDP_NAME, NULL, NULL))
  {
      printf("ERROR: unable to unregister udp\n");
      goto done;
  }

  udp_property = new UDP_InterfaceFactoryProperty();
  if (udp_property == NULL)
  {
      printf("ERROR: unable to allocate udp properties\n");
      goto done;
  }

  udp_property->max_message_size = 65504;

  if (!registry->register_component(
        NETIO_DEFAULT_UDP_NAME,
        UDPInterfaceFactory::get_interface(),
        &udp_property->_parent._parent,
        NULL)) {
      printf("ERROR: unable to register udp\n");
      goto done;
  }

  discovery_plugin_properties = new DPDE::DiscoveryPluginProperty();

  /* Configure properties */
  discovery_plugin_properties->participant_liveliness_assert_period.sec = 5;
  discovery_plugin_properties->participant_liveliness_assert_period.nanosec = 0;
  discovery_plugin_properties->participant_liveliness_lease_duration.sec = 30;
  discovery_plugin_properties->participant_liveliness_lease_duration.nanosec = 0;


  if (!registry->register_component(
        "dpde",
        DPDEDiscoveryFactory::get_interface(),
        &discovery_plugin_properties->_parent,
        NULL)) {
      printf("ERROR: unable to register dpde\n");
      goto done;
  }

  ok = true;
done:
  if (!ok) {
      if (udp_property != NULL) {
          delete udp_property;
      }
      if (discovery_plugin_properties != NULL) {
          delete discovery_plugin_properties;
      }
  }
  return ok;
}

static bool configure_datafrag_size(unsigned int datafrag_size) {

    bool ok = false;
    RT::Registry *registry = NULL;
    UDP_InterfaceFactoryProperty *udp_property = NULL;

    registry = DDSTheParticipantFactory->get_registry();

    if (!registry->unregister(NETIO_DEFAULT_UDP_NAME, NULL, NULL)) {
        printf("ERROR: unable to unregister udp\n");
        goto done;
    }

    udp_property = new UDP_InterfaceFactoryProperty();
    if (udp_property == NULL) {
        printf("ERROR: unable to allocate udp properties\n");
        goto done;
    }

    udp_property->max_message_size = datafrag_size;

    if (!registry->register_component(
            NETIO_DEFAULT_UDP_NAME,
            UDPInterfaceFactory::get_interface(),
            &udp_property->_parent._parent,
            NULL)) {
        printf("ERROR: unable to register udp\n");
        goto done;
    }
    ok = true;
done:
    if (!ok) {
        if (udp_property != NULL) {
            delete udp_property;
        }
    }
    return ok;
}

static bool configure_dp_qos(DDS::DomainParticipantQos &dp_qos)
{
    if (!dp_qos.discovery.discovery.name.set_name("dpde"))
    {
        printf("ERROR: unable to set discovery plugin name\n");
        return false;
    }

    dp_qos.discovery.initial_peers.maximum(2);
    dp_qos.discovery.initial_peers.length(2);
    dp_qos.discovery.initial_peers[0] = DDS_String_dup("127.0.0.1");
    dp_qos.discovery.initial_peers[1] = DDS_String_dup("_udp://239.255.0.1");

    /* if there are more remote or local endpoints, you need to increase these limits */
    dp_qos.resource_limits.max_destination_ports = 32;
    dp_qos.resource_limits.max_receive_ports = 32;
    dp_qos.resource_limits.local_topic_allocation = 8;
    dp_qos.resource_limits.local_type_allocation = 8;

    dp_qos.resource_limits.local_reader_allocation = 8;
    dp_qos.resource_limits.local_writer_allocation = 8;
    dp_qos.resource_limits.remote_participant_allocation = 16;
    dp_qos.resource_limits.remote_reader_allocation = 16;
    dp_qos.resource_limits.remote_writer_allocation = 16;
    return true;
}

void config_dw_qos(DDS::DataWriterQos &dw_qos) {
    dw_qos.resource_limits.max_instances = 500;
    dw_qos.resource_limits.max_samples = 500;
    dw_qos.resource_limits.max_samples_per_instance = 500;
}

void config_dr_qos(DDS::DataReaderQos &dr_qos) {
    dr_qos.resource_limits.max_instances = 500;
    dr_qos.resource_limits.max_samples = 500;
    dr_qos.resource_limits.max_samples_per_instance = 500;
    dr_qos.reader_resource_limits.max_remote_writers = 16;
    dr_qos.reader_resource_limits.max_samples_per_remote_writer = 500;
    dr_qos.reader_resource_limits.max_fragmented_samples = 64;
    dr_qos.reader_resource_limits.max_fragmented_samples_per_remote_writer = 32;
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

void set_instance_color(
        std::vector<std::pair<DDS::InstanceHandle_t, std::string>>& vec,
        const DDS::InstanceHandle_t handle,
        const std::string& color) {
    // Check if the handle already exists
    for (auto& p : vec) {
        if (DDS_InstanceHandle_equals(&p.first, &handle)) {
            return;
        }
    }
    // If it doesn't exist, add it
    vec.push_back(std::make_pair(handle, color));
}

std::string get_instance_color(
        const std::vector<std::pair<DDS::InstanceHandle_t, std::string>>& vec,
        const DDS::InstanceHandle_t handle) {
    for (const auto& p : vec) {
        if (DDS_InstanceHandle_equals(&p.first, &handle)) {
            return p.second;
        }
    }
    return "";
}