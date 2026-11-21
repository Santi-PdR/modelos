#version 150

// Atributos de DefaultVertexFormat.NEW_ENTITY que sí se usan. UV2 (lightmap)
// se deja sin declarar a proposito: en las shaders de entidad es un ivec2 y
// declararlo como vec2 rompe el enlace del atributo.

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in vec3 Normal;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;

out vec2 texCoord;
out vec4 vertexColor;
out float fresnel;

void main() {
    vec4 viewPos = ModelViewMat * vec4(Position, 1.0);

    // Normal en espacio de vista: 1 en el borde que mira de canto, 0 de frente.
    // El epsilon evita normalizar un vector nulo si la reliquia cae en el origen
    // exacto de la camara.
    vec3 viewNormal = normalize(mat3(ModelViewMat) * Normal);
    vec3 viewDir = normalize(-viewPos.xyz + vec3(0.0, 0.0, 0.0001));
    float facing = clamp(abs(dot(viewDir, viewNormal)), 0.0, 1.0);
    fresnel = pow(1.0 - facing, 2.5);

    gl_Position = ProjMat * viewPos;
    texCoord = UV0;
    vertexColor = Color;
}
