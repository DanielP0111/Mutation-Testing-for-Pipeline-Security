project('demo_app', version : '0.1')

# Optional dependency that falls back to a bundled subproject via samplelib.wrap.
# required:false keeps `meson setup` succeeding offline when the dep is absent.
sample = dependency('samplelib', required : false)

feature = get_option('extra')
if feature.enabled()
  message('extra feature on')
endif

message('demo_app configured')
