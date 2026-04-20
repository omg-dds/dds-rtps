cmake_minimum_required(VERSION 3.16)
project(shape LANGUAGES C)

# Find the CycloneDDS package.
find_package(CycloneDDS REQUIRED)
set(EXECUTABLE_NAME "eclipse_cyclone-${CycloneDDS_VERSION}_shape_main_linux")
idlc_generate(TARGET shape_lib FILES "../shape.idl" WARNINGS no-implicit-extensibility)

add_executable(${EXECUTABLE_NAME} ../shape_main.c)

target_compile_definitions(${EXECUTABLE_NAME} PUBLIC -DCYCLONE_DDS)

target_link_libraries(${EXECUTABLE_NAME} shape_lib CycloneDDS::ddsc m)