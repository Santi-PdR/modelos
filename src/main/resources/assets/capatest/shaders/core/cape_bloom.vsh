#version 150

#moj_import <light.glsl>

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in ivec2 UV2;
in vec3 Normal;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;
uniform vec3 Light0_Direction;
uniform vec3 Light1_Direction;

out float vertexDistance;
out vec4 coreTint;
out vec3 haloTint;
flat out vec2 haloGains;
out vec2 texCoord0;

void main() {
    // Same projection and directional term as the stock emissive material.
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);
    vertexDistance = length((ModelViewMat * vec4(Position, 1.0)).xyz);
    coreTint = minecraft_mix_light(Light0_Direction, Light1_Direction, Normal, Color);
    haloTint = Color.rgb;
    // Halo-only payload, not lightmap coordinates (CORE still uses fullbright UV2).
    haloGains = vec2(UV2) / 4096.0;
    texCoord0 = UV0;
}
