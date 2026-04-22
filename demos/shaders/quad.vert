// Vertex shader: fullscreen quad pass-through
// Outputs UV coordinates for the fragment shader.

#version 330 core

in vec2 in_position;   // clip-space position: (-1,-1) to (1,1)
in vec2 in_texcoord;   // UV coordinates: (0,0) to (1,1)

out vec2 v_texcoord;

void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    v_texcoord  = in_texcoord;
}
