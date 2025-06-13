package com.example.demo.domain;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface TestRepository extends JpaRepository<TestEntities, Long> {
    Optional<TestEntities> findByDummyField1AndDummyField2AndDummyField3AndDummyField4(
        String dummyField1,
        String dummyField2,
        String dummyField3,
        String dummyField4,
        String dummyField5
    );
}
