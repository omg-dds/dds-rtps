#include <unistd.h>

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

bool configure_datafrag_size(
        DDS::DomainParticipantQos &dp_qos,
        size_t datafrag_size) {
    bool ok = false;
    if (datafrag_size == 0) {
        ok = false;
    } else {
        if (DDS_PropertyQosPolicyHelper_assert_property(
                &dp_qos.property,
                "dds.transport.UDPv4.builtin.parent.message_size_max",
                std::to_string(datafrag_size).c_str(),
                DDS_BOOLEAN_FALSE) != DDS_RETCODE_OK) {
            ok = false;
            printf("failed to set datafrag_size\n");
        } else {
            ok = true;
        }
    }
    return ok;
}


static bool configure_dp_qos(DDS::DomainParticipantQos &dp_qos) {
    bool ok = false;
    if (!configure_datafrag_size(dp_qos, 65504)) {
        printf("failed to configure dp qos\n");
    } else {
        ok = true;
    }

    return ok;
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

void configure_large_data(DDS::DataWriterQos &dw_qos) {
    if (DDS::PropertyQosPolicyHelper::assert_property(
            dw_qos.property,
            "dds.data_writer.history.memory_manager.fast_pool.pool_buffer_max_size",
            "65536",
            DDS_BOOLEAN_FALSE) != DDS_RETCODE_OK) {
        printf("failed to set property pool_buffer_max_size\n");
    }
    dw_qos.publish_mode.kind = DDS::ASYNCHRONOUS_PUBLISH_MODE_QOS;
}
