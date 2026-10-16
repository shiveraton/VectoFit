cmake_minimum_required(VERSION 3.13)

# Load default React Native C++ config
include(${REACT_ANDROID_DIR}/cmake-utils/ReactNative-application.cmake)

# Include Nitrogen generated autolinking configuration
include("${CMAKE_CURRENT_SOURCE_DIR}/../../../../nitrogen/generated/android/VectoFit+autolinking.cmake")