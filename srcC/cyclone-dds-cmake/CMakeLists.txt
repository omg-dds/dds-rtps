cmake_minimum_required(VERSION 3.16)
project(shape LANGUAGES C)

option(BUILD_SHARED_LIBS "Build using shared libraries by default" ON)

# Find the CycloneDDS package.
find_package(CycloneDDS REQUIRED)
set(EXECUTABLE_NAME "eclipse_cyclone-${CycloneDDS_VERSION}_shape_main_linux")

if(BUILD_SHARED_LIBS)
	idlc_generate(TARGET shape_lib FILES "../shape.idl" WARNINGS no-implicit-extensibility)
else()
	if(NOT EXISTS ${IDLC_ROOT}/idlc)
		message(FATAL_ERROR "The root directory of the idlc executable must be specified using IDLC_ROOT for static builds")
	endif()
	execute_process(COMMAND ${IDLC_ROOT}/idlc shape.idl
			WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}/..
			RESULT_VARIABLE idlc_rez
			OUTPUT_VARIABLE idlc_var)
endif()

add_executable(${EXECUTABLE_NAME} ../shape_main.c)
if(NOT BUILD_SHARED_LIBS)
	add_library(shape_lib shape.c shape.h)
	target_link_libraries(shape_lib CycloneDDS::ddsc m)
endif()

target_compile_definitions(${EXECUTABLE_NAME} PUBLIC -DCYCLONE_DDS)

target_link_libraries(${EXECUTABLE_NAME} shape_lib CycloneDDS::ddsc m)
