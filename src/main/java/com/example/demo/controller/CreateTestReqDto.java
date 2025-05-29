package com.example.demo.controller;

import com.example.demo.service.CreateTestCmd;

public record CreateTestReqDto(
    int id,
    String name
) {
    public CreateTestCmd toCmd() {
        return new CreateTestCmd(id, name);
    }
}
