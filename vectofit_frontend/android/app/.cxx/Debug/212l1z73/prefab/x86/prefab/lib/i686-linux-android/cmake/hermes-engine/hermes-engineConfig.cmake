if(NOT TARGET hermes-engine::hermesvm)
add_library(hermes-engine::hermesvm SHARED IMPORTED)
set_target_properties(hermes-engine::hermesvm PROPERTIES
    IMPORTED_LOCATION "C:/Users/Jhedver/.gradle/caches/8.13/transforms/80f1279535d13c5b3a92e7ce4fe298aa/transformed/hermes-android-250829098.0.17-debug/prefab/modules/hermesvm/libs/android.x86/libhermesvm.so"
    INTERFACE_INCLUDE_DIRECTORIES "C:/Users/Jhedver/.gradle/caches/8.13/transforms/80f1279535d13c5b3a92e7ce4fe298aa/transformed/hermes-android-250829098.0.17-debug/prefab/modules/hermesvm/include"
    INTERFACE_LINK_LIBRARIES ""
)
endif()

