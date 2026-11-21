#version 150

uniform sampler2D Sampler0;
uniform vec4 ColorModulator;
uniform float HoloTime;

in vec2 texCoord;
in vec4 vertexColor;
in float fresnel;

out vec4 fragColor;

void main() {
    vec4 tex = texture(Sampler0, texCoord);
    float alpha = clamp(tex.a * vertexColor.a, 0.0, 1.0);
    if (alpha < 0.02) {
        discard;
    }

    // Linea de barrido que sube por la textura: seis ciclos, 4 s por ciclo.
    float scan = smoothstep(0.45, 0.55, fract(texCoord.y * 6.0 - HoloTime * 0.25));

    vec3 rgb = tex.rgb * vertexColor.rgb + fresnel * 0.35 + scan * 0.06;
    fragColor = vec4(rgb * alpha * ColorModulator.rgb, alpha);
}
