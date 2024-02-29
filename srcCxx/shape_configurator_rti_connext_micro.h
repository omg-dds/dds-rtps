#include "shape_micro.h"
#include "shape_microSupport.h"

#ifndef rti_me_cpp_hxx
  #include "rti_me_cpp.hxx"
#endif

#define LISTENER_STATUS_MASK_ALL (DDS_STATUS_MASK_ALL)

typedef CDR_StringSeq StringSeq;

typedef DDS_Short DataRepresentationId_t;

const DataRepresentationId_t XCDR_DATA_REPRESENTATION = (0x00000001 << 0);
const DataRepresentationId_t XCDR2_DATA_REPRESENTATION = (0x00000001 << 2);

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
