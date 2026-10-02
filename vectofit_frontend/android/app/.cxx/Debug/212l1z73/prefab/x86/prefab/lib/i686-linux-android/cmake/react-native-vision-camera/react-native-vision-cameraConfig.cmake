if(NOT TARGET react-native-vision-camera::VisionCamera)
add_library(react-native-vision-camera::VisionCamera SHARED IMPORTED)
set_target_properties(react-native-vision-camera::VisionCamera PROPERTIES
    IMPORTED_LOCATION "D:/Thesis/VectoFit/vectofit_frontend/node_modules/react-native-vision-camera/android/build/intermediates/cxx/Debug/b4n2o5a1/obj/x86/libVisionCamera.so"
    INTERFACE_INCLUDE_DIRECTORIES "D:/Thesis/VectoFit/vectofit_frontend/node_modules/react-native-vision-camera/android/build/headers/visioncamera"
    INTERFACE_LINK_LIBRARIES ""
)
endif()

