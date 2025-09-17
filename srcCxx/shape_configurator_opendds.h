#include "shapeTypeSupportImpl.h"

#include "dds/DCPS/Marked_Default_Qos.h"
#include "dds/DCPS/Service_Participant.h"

#include "dds/DCPS/RTPS/RtpsDiscovery.h"

#include "dds/DCPS/transport/framework/TransportConfig_rch.h"
#include "dds/DCPS/transport/framework/TransportRegistry.h"
#include "dds/DCPS/transport/rtps_udp/RtpsUdp.h"

#define OBTAIN_DOMAIN_PARTICIPANT_FACTORY TheParticipantFactory
#define LISTENER_STATUS_MASK_ALL OpenDDS::DCPS::ALL_STATUS_MASK
#define REGISTER_TYPE ShapeTypeTypeSupport_var ts = \
    new ShapeTypeTypeSupportImpl; ts->register_type
#define CONFIGURE_PARTICIPANT_FACTORY configure_rtps();
#define STRING_IN .in()
#define STRING_INOUT .inout()
#define STRING_ALLOC(LHS, RHS) LHS = CORBA::string_alloc(RHS)

const char* get_qos_policy_name(DDS::QosPolicyId_t policy_id)
{
  switch (policy_id) {
  case DDS::USERDATA_QOS_POLICY_ID: return "USERDATA";
  case DDS::DURABILITY_QOS_POLICY_ID: return "DURABILITY";
  case DDS::PRESENTATION_QOS_POLICY_ID: return "PRESENTATION";
  case DDS::DEADLINE_QOS_POLICY_ID: return "DEADLINE";
  case DDS::LATENCYBUDGET_QOS_POLICY_ID: return "LATENCYBUDGET";
  case DDS::OWNERSHIP_QOS_POLICY_ID: return "OWNERSHIP";
  case DDS::OWNERSHIPSTRENGTH_QOS_POLICY_ID: return "OWNERSHIPSTRENGTH";
  case DDS::LIVELINESS_QOS_POLICY_ID: return "LIVELINESS";
  case DDS::TIMEBASEDFILTER_QOS_POLICY_ID: return "TIMEBASEDFILTER";
  case DDS::PARTITION_QOS_POLICY_ID: return "PARTITION";
  case DDS::RELIABILITY_QOS_POLICY_ID: return "RELIABILITY";
  case DDS::DESTINATIONORDER_QOS_POLICY_ID: return "DESTINATIONORDER";
  case DDS::HISTORY_QOS_POLICY_ID: return "HISTORY";
  case DDS::RESOURCELIMITS_QOS_POLICY_ID: return "RESOURCELIMITS";
  case DDS::ENTITYFACTORY_QOS_POLICY_ID: return "ENTITYFACTORY";
  case DDS::WRITERDATALIFECYCLE_QOS_POLICY_ID: return "WRITERDATALIFECYCLE";
  case DDS::READERDATALIFECYCLE_QOS_POLICY_ID: return "READERDATALIFECYCLE";
  case DDS::TOPICDATA_QOS_POLICY_ID: return "TOPICDATA";
  case DDS::GROUPDATA_QOS_POLICY_ID: return "GROUPDATA";
  case DDS::TRANSPORTPRIORITY_QOS_POLICY_ID: return "TRANSPORTPRIORITY";
  case DDS::LIFESPAN_QOS_POLICY_ID: return "LIFESPAN";
  case DDS::DURABILITYSERVICE_QOS_POLICY_ID: return "DURABILITYSERVICE";
  default: return "Unknown";
  }
}

void StringSeq_push(DDS::StringSeq& string_seq, const char* elem)
{
  const unsigned int i = string_seq.length();
  string_seq.length(i + 1);
  string_seq[i] = elem;
}

template <typename Seq>
DDS::UInt32 DDS_UInt8Seq_get_length(const Seq* seq)
{
  return seq->length();
}

template <typename Seq>
void DDS_UInt8Seq_ensure_length(Seq* seq, DDS::UInt32 len, DDS::UInt32 = 0)
{
  seq->length(len);
}

template <typename Seq>
DDS::UInt8* DDS_UInt8Seq_get_reference(Seq* seq, DDS::UInt32 idx)
{
  return &(*seq)[idx];
}

template <typename Seq>
const DDS::UInt8* DDS_UInt8Seq_get_reference(const Seq* seq, DDS::UInt32 idx)
{
  return &(*seq)[idx];
}

void configure_rtps()
{
  using namespace OpenDDS::DCPS;
  using namespace OpenDDS::RTPS;
  TransportConfig_rch config =
    TransportRegistry::instance()->create_config("rtps_interop_demo");
  TransportInst_rch inst =
    TransportRegistry::instance()->create_inst("rtps_transport","rtps_udp");
  config->instances_.push_back(inst);
  TransportRegistry::instance()->global_config(config);

  RtpsDiscovery_rch disc = make_rch<RtpsDiscovery>("RtpsDiscovery");
  disc->use_xtypes(RtpsDiscoveryConfig::XTYPES_NONE);
  TheServiceParticipant->add_discovery(static_rchandle_cast<Discovery>(disc));
  TheServiceParticipant->set_default_discovery(disc->key());
}
