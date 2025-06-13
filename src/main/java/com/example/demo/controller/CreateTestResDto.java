package com.example.demo.controller;

public record CreateTestResDto(
    int id,
    String name
) {
    public static CreateTestResDto from(CreateTestRes) {}
}
