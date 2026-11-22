#version 150

uniform sampler2D Sampler0;
uniform vec4 ColorModulator;
uniform float HoloTime;

in vec2 texCoord;
in vec4 vertexColor;
in float edge;
in float viewY;

out vec4 fragColor;

// Ruido barato y deterministico: rompe el banding que deja el blend aditivo
// cuando el degradado es muy suave. Sin tiempo dentro a proposito: si cambia por
// frame, en vez de dither se ve hervir.
float hash(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
    vec4 tex = texture(Sampler0, texCoord);
    float texAlpha = tex.a * vertexColor.a;

    // Dos bordes por multiplicacion, no por pow: el suave tine la cara y el
    // cuarto se queda pegado a la silueta. Dos multiplicaciones cuestan menos
    // que dos pow y el corte del borde queda mas limpio.
    float e = clamp(edge, 0.0, 1.0);
    float rimSoft = e * e;
    float rimTight = rimSoft * rimSoft;

    // El borde entra tambien en la alpha: la silueta brilla aunque ahi la
    // textura emisiva sea transparente. Es lo que lo hace leer como contorno de
    // holograma y no como un brillo pegado encima de las caras opacas.
    float alpha = max(texAlpha, rimSoft * 0.55 + rimTight * 0.30);
    if (alpha < 0.02) {
        discard;
    }

    // Barrido: una banda que sube por la reliquia entera, un ciclo cada 4 s.
    float sweep = smoothstep(0.40, 0.62, fract(viewY * 0.9 - HoloTime * 0.25));
    // Rejilla fina, anclada al espacio de vista: las lineas siguen de una cara a
    // otra y no se pelean entre caras al girar la camara.
    float grid = 0.5 + 0.5 * sin(viewY * 90.0 + HoloTime * 3.0);
    // Latido lento del borde. No toca el nucleo: eso es la textura por el tinte.
    float breath = 0.85 + 0.15 * sin(HoloTime * 1.6);

    vec3 tint = vertexColor.rgb;
    vec3 rimTint = mix(vec3(0.55, 0.85, 1.0), tint, 0.55);
    // Al raspar, el borde se va al violeta: dos tonos en la misma silueta.
    rimTint = mix(rimTint, vec3(0.78, 0.62, 1.0), rimTight * 0.35);

    vec3 rgb = tex.rgb * tint
             + rimSoft * rimTint * 0.28 * breath
             + rimTight * rimTint * 0.45
             + sweep * 0.07
             + grid * texAlpha * 0.02
             + (hash(texCoord * 613.0) - 0.5) * 0.03;

    fragColor = vec4(rgb * alpha * ColorModulator.rgb, alpha);
}
