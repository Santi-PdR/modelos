#version 150

uniform sampler2D Sampler0;
uniform vec4 ColorModulator;
uniform float HoloTime;

in vec2 texCoord;
in vec4 vertexColor;
in float edge;

out vec4 fragColor;

// Ruido barato y deterministico: rompe el banding que deja el blend aditivo
// cuando el degradado es muy suave.
float hash(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
    vec4 tex = texture(Sampler0, texCoord);
    float texAlpha = tex.a * vertexColor.a;

    // Borde: sale de la posicion del vertice, no de la alpha de la textura, asi
    // que la silueta brilla aunque ese texel de la textura emisiva sea
    // transparente. Es lo que hace que se lea como un contorno de holograma y no
    // como un brillo pegado encima de las caras opacas.
    float rim = pow(clamp(edge, 0.0, 1.0), 1.6);
    float alpha = max(texAlpha, rim * 0.55);
    if (alpha < 0.02) {
        discard;
    }

    // Barrido que sube: cuatro ciclos sobre la textura, uno cada 4 s.
    float sweep = smoothstep(0.42, 0.58, fract(texCoord.y * 4.0 - HoloTime * 0.25));
    // Barrido cruzado, mas rapido y mas tenue: rompe la simetria del vertical.
    float cross = smoothstep(0.46, 0.54, fract((texCoord.x + texCoord.y) * 2.0 - HoloTime * 0.41));
    // Lineas finas de holograma, solo donde ya hay algo opaco.
    float lines = (0.5 + 0.5 * sin(texCoord.y * 160.0 + HoloTime * 5.0)) * texAlpha;

    vec3 tint = vertexColor.rgb;
    vec3 rimTint = mix(vec3(0.55, 0.85, 1.0), tint, 0.55);

    vec3 rgb = tex.rgb * tint
             + rim * rimTint * 0.40
             + (sweep * 0.06 + cross * 0.045 + lines * 0.02)
             + (hash(texCoord * 613.0) - 0.5) * 0.03;

    fragColor = vec4(rgb * alpha * ColorModulator.rgb, alpha);
}
