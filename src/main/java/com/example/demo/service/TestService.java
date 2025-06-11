package com.example.demo.service;

import com.example.demo.controller.CreateTestReqDto;
import com.example.demo.controller.CreateTestResDto;
import com.example.demo.domain.TestEntities;
import com.example.demo.domain.TestRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class TestService {
    private final TestRepository testRepository;

    public CreateTestResult saveTestEntities1(CreateTestCmd cmd) {
        TestEntities entities = TestEntities.create(cmd.name());
        TestEntities newEntity = testRepository.save(entities);

        return CreateTestResult.of(newEntity);
    }

    public CreateTestResDto saveTestEntities2(CreateTestReqDto req) {
        TestEntities entities = TestEntities.create(req.name());
        TestEntities newEntity = testRepository.save(entities);

        return new CreateTestResDto(newEntity.getId(), newEntity.getName());
    }
}
