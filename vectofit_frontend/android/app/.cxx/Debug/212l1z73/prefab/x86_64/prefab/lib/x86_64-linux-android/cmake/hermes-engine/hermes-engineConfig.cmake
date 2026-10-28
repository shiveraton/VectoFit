if(NOT TARGET hermes-engine::hermesvm)
add_library(hermes-engine::hermesvm SHARED IMPORTED)
set_target_properties(hermes-engine::hermesvm PROPERTIES
    IMPORTED_LOCATION "C:/Users/Jhedver/.gradle/caches/8.13/transforms/444b2e5b2f0731a4d837df2835ddd121/transformed/hermes-android-250829098.0.17-debug/prefab/modules/hermesvm/libs/android.x86_64/libhermesvm.so"
    INTERFACE_INCLUDE_DIRECTORIES "C:/Users/Jhedver/.gradle/caches/8.13/transforms/444b2e5b2f0731a4d837df2835ddd121/transformed/hermes-android-250829098.0.17-debug/prefab/modules/hermesvm/include"
    INTERFACE_LINK_LIBRARIES ""
)
endif()

