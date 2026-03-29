#ifndef _SHAPE_CONFIG_CYCLONE_
#define _SHAPE_CONFIG_CYCLONE_

#include "shape.h"
#include "dds/dds.h"
#include <string.h>
#include <dds/ddsc/dds_public_qosdefs.h>
#include <dds/ddsc/dds_public_status.h>
#include <dds/ddsc/dds_public_qosdefs.h>
#include <dds/ddsrt/time.h>
#include <stddef.h>
#include <stdint.h>

const char* get_qos_policy_name(uint32_t last_policy_id) {

    switch (last_policy_id) {
        case DDS_INVALID_QOS_POLICY_ID: return "INVALID"; 
        case DDS_USERDATA_QOS_POLICY_ID: return "USERDATA"; 
        case DDS_DURABILITY_QOS_POLICY_ID: return "DURABILITY"; 
        case DDS_PRESENTATION_QOS_POLICY_ID: return "PRESENTATION"; 
        case DDS_DEADLINE_QOS_POLICY_ID: return "DEADLINE"; 
        case DDS_LATENCYBUDGET_QOS_POLICY_ID: return "LATENCYBUDGET"; 
        case DDS_OWNERSHIP_QOS_POLICY_ID: return "OWNERSHIP"; 
        case DDS_OWNERSHIPSTRENGTH_QOS_POLICY_ID: return "OWNERSHIPSTRENGTH"; 
        case DDS_LIVELINESS_QOS_POLICY_ID: return "LIVELINESS"; 
        case DDS_TIMEBASEDFILTER_QOS_POLICY_ID: return "TIMEBASEDFILTER"; 
        case DDS_PARTITION_QOS_POLICY_ID: return "PARTITION"; 
        case DDS_RELIABILITY_QOS_POLICY_ID: return "RELIABILITY"; 
        case DDS_DESTINATIONORDER_QOS_POLICY_ID: return "DESTINATIONORDER"; 
        case DDS_HISTORY_QOS_POLICY_ID: return "HISTORY"; 
        case DDS_RESOURCELIMITS_QOS_POLICY_ID: return "RESOURCELIMITS"; 
        case DDS_ENTITYFACTORY_QOS_POLICY_ID: return "ENTITYFACTORY"; 
        case DDS_WRITERDATALIFECYCLE_QOS_POLICY_ID: return "WRITERDATALIFECYCLE"; 
        case DDS_READERDATALIFECYCLE_QOS_POLICY_ID: return "READERDATALIFECYCLE"; 
        case DDS_TOPICDATA_QOS_POLICY_ID: return "TOPICDATA"; 
        case DDS_GROUPDATA_QOS_POLICY_ID: return "GROUPDATA"; 
        case DDS_TRANSPORTPRIORITY_QOS_POLICY_ID: return "TRANSPORTPRIORITY"; 
        case DDS_LIFESPAN_QOS_POLICY_ID: return "LIFESPAN"; 
        case DDS_DURABILITYSERVICE_QOS_POLICY_ID: return "DURABILITYSERVICE"; 
        case DDS_PROPERTY_QOS_POLICY_ID: return "PROPERTY"; 
        case DDS_TYPE_CONSISTENCY_ENFORCEMENT_QOS_POLICY_ID: return "TYPE_CONSISTENCY_ENFORCEMENT"; 
        case DDS_DATA_REPRESENTATION_QOS_POLICY_ID: return "DATAREPRESENTATION";
        default:
            return 0; 
    }
}

#endif


