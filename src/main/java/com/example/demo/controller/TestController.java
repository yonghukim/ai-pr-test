package com.example.demo.controller;

import com.example.demo.domain.TestEntities;
import com.example.demo.domain.TestRepository;
import com.example.demo.service.CreateTestResult;
import com.example.demo.service.TestService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/test")
@RequiredArgsConstructor
public class TestController {
    private final TestService testService;
    private final TestRepository testRepository;

    @PostMapping("/method1")
    public CreateTestResDto good(CreateTestReqDto req) {
        CreateTestResult testResult = testService.saveTestEntities1(req.toCmd());
        return new CreateTestResDto(req.id(), req.name());
    }

    @PostMapping("/method2")
    public CreateTestOutDto bad(CreateTestInDto req) {
        return new CreateTestOutDto(req.getId(), req.getName());
    }

    @PostMapping
    public TestEntities create() {
        TestEntities entities = TestEntities.create();
        return testRepository.save(entities);
    }
}
