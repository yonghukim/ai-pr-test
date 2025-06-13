package com.example.demo.service;

import com.example.demo.domain.TestEntities;

public record CreateTestResult(
        int id,
        String name
) {
    public static CreateTestResult of(TestEntities entity) {
        return new CreateTestResult(
                entity.getId(),
                entity.getName()
        );
    }
}
