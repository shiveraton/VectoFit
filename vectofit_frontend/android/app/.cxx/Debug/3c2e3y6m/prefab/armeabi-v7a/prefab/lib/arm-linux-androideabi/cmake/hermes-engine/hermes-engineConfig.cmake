if(NOT TARGET hermes-engine::hermesvm)
add_library(hermes-engine::hermesvm SHARED IMPORTED)
set_target_properties(hermes-engine::hermesvm PROPERTIES
    IMPORTED_LOCATION "C:/Users/Jhedver/.gradle/caches/9.4.1/transforms/7f7ae9f0c85853308d8eb5a96ca59448/transformed/hermes-android-260318099.0.4-debug/prefab/modules/hermesvm/libs/android.armeabi-v7a/libhermesvm.so"
    INTERFACE_INCLUDE_DIRECTORIES "C:/Users/Jhedver/.gradle/caches/9.4.1/transforms/7f7ae9f0c85853308d8eb5a96ca59448/transformed/hermes-android-260318099.0.4-debug/prefab/modules/hermesvm/include"
    INTERFACE_LINK_LIBRARIES ""
)
endif()

