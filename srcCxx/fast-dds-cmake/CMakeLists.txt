# Copyright 2023 Proyectos y Sistemas de Mantenimiento SL (eProsima).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

cmake_minimum_required(VERSION 3.16.3)

project(eprosima-fastdds_shape_main_linux LANGUAGES CXX)

# Find requirements
set(FASTDDS_STATIC ON)
find_package(fastcdr REQUIRED)
find_package(fastdds REQUIRED)
find_program(FASTDDSGEN fastddsgen)

# Generate code from IDL
file(MAKE_DIRECTORY ${CMAKE_SOURCE_DIR}/../GeneratedCode)
set(
  GENERATED_TYPE_SUPPORT_SOURCES
  ${CMAKE_SOURCE_DIR}/../GeneratedCode/shapePubSubTypes.cxx
  ${CMAKE_SOURCE_DIR}/../GeneratedCode/shapeTypeObjectSupport.cxx
)
set(
  GENERATED_TYPE_SUPPORT_FILES
  ${CMAKE_SOURCE_DIR}/../GeneratedCode/shape.hpp
  ${CMAKE_SOURCE_DIR}/../GeneratedCode/shapeCdrAux.hpp
  ${CMAKE_SOURCE_DIR}/../GeneratedCode/shapeCdrAux.ipp
  ${CMAKE_SOURCE_DIR}/../GeneratedCode/shapePubSubTypes.cxx
  ${CMAKE_SOURCE_DIR}/../GeneratedCode/shapePubSubTypes.hpp
  ${CMAKE_SOURCE_DIR}/../GeneratedCode/shapeTypeObjectSupport.cxx
  ${CMAKE_SOURCE_DIR}/../GeneratedCode/shapeTypeObjectSupport.hpp
)
add_custom_command(
  OUTPUT ${GENERATED_TYPE_SUPPORT_FILES}
  COMMAND ${FASTDDSGEN}
  -replace
  -d ${CMAKE_SOURCE_DIR}/../GeneratedCode
  -flat-output-dir
  ${CMAKE_SOURCE_DIR}/../shape.idl
  DEPENDS ${CMAKE_SOURCE_DIR}/../shape.idl
  COMMENT "Generating code with Fast DDS Gen" VERBATIM
)

message(STATUS "Configuring application...")
set(EXECUTABLE_NAME "eprosima_fastdds-${fastdds_VERSION}_shape_main_linux")
add_executable(${EXECUTABLE_NAME}
    ../shape_main.cxx
    ${GENERATED_TYPE_SUPPORT_SOURCES}
    )
target_compile_definitions(${EXECUTABLE_NAME} PRIVATE EPROSIMA_FAST_DDS=1)
target_link_libraries(${EXECUTABLE_NAME} fastdds)
