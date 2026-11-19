#version 150

#moj_import <fog.glsl>

uniform sampler2D Sampler0;
uniform sampler2D Sampler1;
uniform vec4 ColorModulator;
uniform float FogStart;
uniform float FogEnd;

in float vertexDistance;
in vec4 coreTint;
in vec3 haloTint;
flat in vec2 haloGains;
in vec2 texCoord0;

out vec4 fragColor;

void main() {
    vec4 core = texture(Sampler0, texCoord0);
    vec3 halo = texture(Sampler1, texCoord0).rgb;
    if (core.a < 0.1) core.a = 0.0;
    if (core.a == 0.0 && halo.r == 0.0 && halo.b == 0.0) discard;

    float fade = linear_fog_fade(vertexDistance, FogStart, FogEnd);
    float cover = core.a * coreTint.a * ColorModulator.a;
    float alpha = cover * fade;
    // Keep the fallback core and softly add light in its uncovered fraction.
    // A colored halo texel alone must never darken a lit fabric or write depth.
    // The low-energy skirt peaks after the lip of the crack in darkness.
    float closeToCore = smoothstep(0.04, 0.36, halo.r);
    float gain = mix(haloGains.x, haloGains.y, closeToCore);
    vec3 light = core.rgb * coreTint.rgb * (alpha * fade);
    light += halo * haloTint * ((1.0 - cover) * (0.45 + 0.55 * haloTint.r) * gain * ColorModulator.a * fade);
    fragColor = vec4(light * ColorModulator.rgb, alpha);
}
