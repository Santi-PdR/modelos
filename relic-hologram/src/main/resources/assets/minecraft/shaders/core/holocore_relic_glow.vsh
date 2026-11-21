#version 150

// Atributos de DefaultVertexFormat.NEW_ENTITY que se usan. UV1 (overlay) y UV2
// (lightmap) se dejan sin declarar a proposito: en las shaders de entidad son
// ivec2 y declararlos como vec2 rompe el enlace del atributo.

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in vec3 Normal;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;

out vec2 texCoord;
out vec4 vertexColor;
out float edge;

void main() {
    vec4 viewPos = ModelViewMat * vec4(Position, 1.0);
    vec3 viewDir = normalize(-viewPos.xyz + vec3(0.0, 0.0, 0.0001));

    // Direccion hacia fuera: la reliquia esta centrada en el origen del modelo
    // (preRender no aplica desplazamiento), asi que la posicion del vertice ya
    // apunta hacia fuera. Se usa esto y no solo la normal porque el atributo
    // Normal puede venir igual en todas las caras segun lo rellene el modelo:
    // entonces el fresnel dejaria de seguir la silueta y seria un tinte plano.
    vec3 outward = normalize(Position + vec3(0.0, 0.0, 0.0001));
    vec3 viewOutward = normalize(mat3(ModelViewMat) * outward);

    // Un cuarto de normal (si viene bien puesta) matiza el borde sin depender
    // de ella. El epsilon va dentro del normalize y no en un ternario: hay
    // drivers que evaluan las dos ramas y normalize(vec3(0.0)) da NaN.
    vec3 viewNormal = normalize(mat3(ModelViewMat) * Normal + vec3(0.0, 0.0, 0.0001));
    vec3 basis = normalize(viewOutward * 0.75 + viewNormal * 0.25);

    // 1 de canto (borde de la silueta), 0 de frente.
    edge = 1.0 - clamp(abs(dot(viewDir, basis)), 0.0, 1.0);

    gl_Position = ProjMat * viewPos;
    texCoord = UV0;
    vertexColor = Color;
}
