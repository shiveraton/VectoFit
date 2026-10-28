if(NOT TARGET kolibri-android::kolibri)
add_library(kolibri-android::kolibri STATIC IMPORTED)
set_target_properties(kolibri-android::kolibri PROPERTIES
    IMPORTED_LOCATION "C:/Users/Jhedver/.gradle/caches/9.4.1/transforms/06a7350c3243cdc5d7f10c0dc82d2e7e/transformed/kolibri-android-0.2.3/prefab/modules/kolibri/libs/android.armeabi-v7a/libkolibri.a"
    INTERFACE_INCLUDE_DIRECTORIES "C:/Users/Jhedver/.gradle/caches/9.4.1/transforms/06a7350c3243cdc5d7f10c0dc82d2e7e/transformed/kolibri-android-0.2.3/prefab/modules/kolibri/include"
    INTERFACE_LINK_LIBRARIES ""
)
endif()

