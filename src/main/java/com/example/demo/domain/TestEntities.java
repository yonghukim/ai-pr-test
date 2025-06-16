package com.example.demo.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

// target branch test
@Entity
@NoArgsConstructor
@Setter
@Getter
public class TestEntities {
    @Id
    private int id;

    @Column(name = "name")
    private String name;

    @Enumerated(EnumType.STRING)
    private TestEnum testEnum = TestEnum.TEST1;

    @Version
    private int version;

    private int dummyField1 = 1;
    private int dummyField2 = 1;
    private int dummyField3 = 1;
    private int dummyField4 = 1;
    private int dummyField5 = 1;

    public static TestEntities create(String name) {
        TestEntities testEntities = new TestEntities();
        testEntities.name = name;
        testEntities.setTestEnum(TestEnum.TEST1);
        testEntities.setVersion(1);
        return testEntities;
    }
}

enum TestEnum {
    TEST1,
    TEST2,
    TEST3;
}

