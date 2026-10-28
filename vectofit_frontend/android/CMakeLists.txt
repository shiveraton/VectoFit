cmake_minimum_required(VERSION 3.13)

project(appmodules)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(${REACT_ANDROID_DIR}/cmake-utils/ReactNative-application.cmake)

find_package(react-native-vision-camera REQUIRED)

add_library(
    VectoFit
    SHARED
    "${CMAKE_CURRENT_SOURCE_DIR}/app/src/main/cpp/cpp-adapter.cpp"
)

include(
    "${CMAKE_CURRENT_SOURCE_DIR}/../nitrogen/generated/android/VectoFit+autolinking.cmake"
)

find_library(LOG_LIB log)

target_link_libraries(
    VectoFit
    ${LOG_LIB}
    android
    react-native-vision-camera::VisionCamera
)