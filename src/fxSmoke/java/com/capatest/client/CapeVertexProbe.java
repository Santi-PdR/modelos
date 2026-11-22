package com.capatest.client;

import com.mojang.blaze3d.vertex.VertexConsumer;

/** Read-only sink for the actual submitted color and light coordinates. */
final class CapeVertexProbe implements VertexConsumer {
    int count, light, rgba;
    float minU = Float.POSITIVE_INFINITY, maxU = Float.NEGATIVE_INFINITY;
    float minV = Float.POSITIVE_INFINITY, maxV = Float.NEGATIVE_INFINITY;

    @Override public VertexConsumer vertex(double x, double y, double z) { return this; }
    @Override public VertexConsumer color(int r, int g, int b, int a) { rgba = r << 24 | g << 16 | b << 8 | a; return this; }
    @Override public VertexConsumer uv(float u, float v) {
        minU = Math.min(minU, u); maxU = Math.max(maxU, u);
        minV = Math.min(minV, v); maxV = Math.max(maxV, v);
        return this;
    }
    @Override public VertexConsumer overlayCoords(int u, int v) { return this; }
    @Override public VertexConsumer uv2(int u, int v) { light = (u & 0xffff) | v << 16; return this; }
    @Override public VertexConsumer normal(float x, float y, float z) { return this; }
    @Override public void endVertex() { count++; }
    @Override public void defaultColor(int r, int g, int b, int a) {}
    @Override public void unsetDefaultColor() {}
}
