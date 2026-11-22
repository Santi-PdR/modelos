#version 150

uniform sampler2D Sampler0;
uniform vec4 ColorModulator;
uniform float HoloTime;
uniform float HoloGlitch;
uniform vec4 HoloTint;

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
    // Glitch de evento (destello, pulso, golpe): la UV se parte por bandas
    // horizontales y los canales se separan. Va en una rama sobre un uniform, o
    // sea la misma para todos los pixeles del dibujo, asi que el camino normal
    // sigue muestreando la textura una sola vez.
    vec2 uv = texCoord;
    if (HoloGlitch > 0.01) {
        float band = floor(viewY * 48.0);
        float tear = (hash(vec2(band, floor(HoloTime * 14.0))) - 0.5) * HoloGlitch * 0.08;
        uv.x += tear;
    }

    vec4 tex = texture(Sampler0, uv);
    vec3 texRgb = tex.rgb;
    if (HoloGlitch > 0.01) {
        float split = HoloGlitch * 0.010;
        texRgb = vec3(texture(Sampler0, uv + vec2(split, 0.0)).r,
                      tex.r,
                      texture(Sampler0, uv - vec2(split, 0.0)).b);
    }
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
    // HoloTint lo pone el renderer por estado de brillo (0.62 en lluvia, 1.08 en la
    // oscuridad): el tinte del borde lo respeta, si no todos los estados acababan
    // con el mismo azul en la silueta.
    vec3 rimTint = mix(vec3(0.55, 0.85, 1.0), tint, 0.55) * HoloTint.rgb;
    // Al raspar, el borde se va al violeta: dos tonos en la misma silueta.
    rimTint = mix(rimTint, vec3(0.78, 0.62, 1.0), rimTight * 0.35);

    vec3 rgb = texRgb * tint
             + rimSoft * rimTint * 0.28 * breath
             + rimTight * rimTint * 0.45
             + sweep * 0.07
             + grid * texAlpha * 0.02
             + (hash(texCoord * 613.0) - 0.5) * 0.03;

    fragColor = vec4(rgb * alpha * ColorModulator.rgb, alpha);
}
