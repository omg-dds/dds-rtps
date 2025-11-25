#include "shape.h"
#include <InterCOM/ccpp_dds_dcps.h>
#include <InterCOM/dds_curr_dcps.h>

#define StringSeq_push(seq, val) seq.push_back(val)
#define LISTENER_STATUS_MASK_ALL STATUS_MASK_ALL
#define REGISTER_TYPE ShapeTypeTypeSupport::get_instance()->register_type
#define STRING_IN .c_str()
#define STRING_ASSIGN(a, b) a = b
#define STRING_FREE static_cast<void>

#define DDS_UInt8Seq_get_length(s)         (s)->size()
#define DDS_UInt8Seq_ensure_length(s,l,x)  (s)->resize(l)
#define DDS_UInt8Seq_get_reference(s,l)    &( (*s)[l] )

#define DDS_BOOLEAN_TRUE                   true
#define DDS_BOOLEAN_FALSE                  false

inline const char *get_qos_policy_name(DDS::QosPolicyId_t policy_id) {
  switch (policy_id) {
  case DDS::USERDATA_QOS_POLICY_ID:
    return "USERDATA";
  case DDS::DURABILITY_QOS_POLICY_ID:
    return "DURABILITY";
  case DDS::PRESENTATION_QOS_POLICY_ID:
    return "PRESENTATION";
  case DDS::DEADLINE_QOS_POLICY_ID:
    return "DEADLINE";
  case DDS::LATENCYBUDGET_QOS_POLICY_ID:
    return "LATENCYBUDGET";
  case DDS::OWNERSHIP_QOS_POLICY_ID:
    return "OWNERSHIP";
  case DDS::OWNERSHIPSTRENGTH_QOS_POLICY_ID:
    return "OWNERSHIPSTRENGTH";
  case DDS::LIVELINESS_QOS_POLICY_ID:
    return "LIVELINESS";
  case DDS::TIMEBASEDFILTER_QOS_POLICY_ID:
    return "TIMEBASEDFILTER";
  case DDS::PARTITION_QOS_POLICY_ID:
    return "PARTITION";
  case DDS::RELIABILITY_QOS_POLICY_ID:
    return "RELIABILITY";
  case DDS::DESTINATIONORDER_QOS_POLICY_ID:
    return "DESTINATIONORDER";
  case DDS::HISTORY_QOS_POLICY_ID:
    return "HISTORY";
  case DDS::RESOURCELIMITS_QOS_POLICY_ID:
    return "RESOURCELIMITS";
  case DDS::ENTITYFACTORY_QOS_POLICY_ID:
    return "ENTITYFACTORY";
  case DDS::WRITERDATALIFECYCLE_QOS_POLICY_ID:
    return "WRITERDATALIFECYCLE";
  case DDS::READERDATALIFECYCLE_QOS_POLICY_ID:
    return "READERDATALIFECYCLE";
  case DDS::TOPICDATA_QOS_POLICY_ID:
    return "TOPICDATA";
  case DDS::GROUPDATA_QOS_POLICY_ID:
    return "GROUPDATA";
  case DDS::TRANSPORTPRIORITY_QOS_POLICY_ID:
    return "TRANSPORTPRIORITY";
  case DDS::LIFESPAN_QOS_POLICY_ID:
    return "LIFESPAN";
  case DDS::DURABILITYSERVICE_QOS_POLICY_ID:
    return "DURABILITYSERVICE";
  case DDS::DATA_REPRESENTATION_QOS_POLICY_ID:
    return "DATAREPRESENTATION";
  default:
    return "Unknown";
  }
}