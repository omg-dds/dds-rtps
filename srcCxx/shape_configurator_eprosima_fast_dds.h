#include <fastdds/dds/domain/DomainParticipant.hpp>
#include <fastdds/dds/domain/DomainParticipantFactory.hpp>
#include <fastdds/dds/domain/DomainParticipantListener.hpp>
#include <fastdds/dds/publisher/Publisher.hpp>
#include <fastdds/dds/publisher/DataWriter.hpp>
#include <fastdds/dds/publisher/DataWriterListener.hpp>
#include <fastdds/dds/subscriber/Subscriber.hpp>
#include <fastdds/dds/subscriber/DataReader.hpp>
#include <fastdds/dds/subscriber/DataReaderListener.hpp>
#include <fastdds/dds/subscriber/qos/DataReaderQos.hpp>
#include <fastdds/dds/subscriber/SampleInfo.hpp>
#include <fastdds/dds/topic/TypeSupport.hpp>

#include "GeneratedCode/shape.hpp"
#include "GeneratedCode/shapePubSubTypes.hpp"

#define LISTENER_STATUS_MASK_ALL StatusMask::all()
#define LISTENER_STATUS_MASK_NONE StatusMask::none()
#define REGISTER_TYPE TypeSupport ts(new ShapeTypePubSubType()); ts.register_type
#define STRING_ASSIGN(field, value) field() = value
#define STRING_IN .c_str()
#define NAME_ACCESSOR .c_str()
#define FIELD_ACCESSOR ()
#define GET_TOPIC_DESCRIPTION(dr) const_cast<TopicDescription*>(dr->get_topicdescription())
#define ADD_PARTITION(field, value) field().push_back(value)
#define SECONDS_FIELD_NAME seconds

#define ShapeTypeDataReader DataReader
#define ShapeTypeDataWriter DataWriter
#define StringSeq std::vector<std::string>

namespace DDS = eprosima::fastdds::dds;
#define RETCODE_OK DDS::RETCODE_OK

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

uint64_t DDS_UInt8Seq_get_length(const std::vector<unsigned char>* seq)
{
  return seq->size();
}
