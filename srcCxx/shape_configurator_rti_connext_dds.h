#include "shape.h"
#include "shapeSupport.h"
#include "ndds/ndds_namespace_cpp.h"

#define LISTENER_STATUS_MASK_ALL (DDS_STATUS_MASK_ALL)

void StringSeq_push(DDS::StringSeq  &string_seq, const char *elem)
{
    string_seq.ensure_length(string_seq.length()+1, string_seq.length()+1);
    string_seq[string_seq.length()-1] = DDS_String_dup(elem);
}

const char *get_qos_policy_name(DDS_QosPolicyId_t policy_id)
{
    return DDS_QosPolicyId_to_string(policy_id); // not standard...
}

void configure_participant_announcements_period(
        DDS::DomainParticipantQos &dp_qos,
        useconds_t announcement_period_us) {
    if (announcement_period_us == 0) {
        return;
    }
    dp_qos.discovery_config.participant_liveliness_assert_period.sec =
            announcement_period_us / 1000000;
    dp_qos.discovery_config.participant_liveliness_assert_period.nanosec =
            (announcement_period_us % 1000000) * 1000;
}
