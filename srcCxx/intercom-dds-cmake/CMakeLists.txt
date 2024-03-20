cmake_minimum_required(VERSION 3.16.3)

project(intercom-dds_shape_main_linux LANGUAGES CXX)

find_package(InterCOM REQUIRED)

cidl_generate( ${CMAKE_CURRENT_LIST_DIR}/../shape.idl DESTINATION gen )
set(EXECUTABLE_NAME "intercom_dds-${InterCOM_VERSION}_shape_main_linux")
add_executable(${EXECUTABLE_NAME}
    ${CMAKE_CURRENT_LIST_DIR}/../shape_main.cxx
    ${CIDL_GENERATE_OUTPUTS}
    )
target_compile_definitions(${EXECUTABLE_NAME} PRIVATE INTERCOM_DDS=1)
target_link_libraries(${EXECUTABLE_NAME} InterCOM::intercom_static)
target_include_directories(${EXECUTABLE_NAME} PUBLIC ${CMAKE_CURRENT_BINARY_DIR}/gen)