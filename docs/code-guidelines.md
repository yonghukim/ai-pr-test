## Spring service 관련

- Service 를 만들때 구현체가 여러개가 아니라면 interface를 만들지 않는다.
## JPA
- JpaRepository 메소드 이름이 너무 길어지는 경우에 default 인터페이스를 추가해서 이름을 읽기 편한 이름으로 변경해주도록 한다.
- 쿼리 DSL을 지향하고 쿼리 DSL이 안되는 쿼리 인 경우 JPQL사용을 허용

## QueryDSL
domain 모듈안에서 만드는 Projection Class 라면`@QueryProjection` 을 사용한다.

## entity
- entity 디렉토리에는 entity만 넣어두도록 한다. enum, type 같은것들은 다른 디렉토리로 뺀다.
```java
//BAD
package com.example.domain.entity.SomeEnum;

//GOOD
package com.example.domain.enums.SomeEnum
```
- entity 내부에서 생성 로직들은 추가하지 않는다, 생성이 필요한경우 mapper 나 따로 변환 util 클래스를 추가해서 사용한다.
```java
// BAD
@Entity
class SomeEntity {
    public static SomeEntity create(String name) {
        SomeEntity entity = new SomeEntity();
        entity.name = name;
        return entity;
    }
}

// GOOD
@Entity
class SomeEntity {
}

public class SomeEntityMapper {
    public static SomeEntity create(String name) {
        SomeEntity entity = new SomeEntity();
        entity.setName(name);
        return entity;
    }
}
```
- 이름은 단수로 짓는다.
- @Setter 사용을 지양한다.
```java
// BAD
@Entity
@Setter
class SomeEntity {
    private String name;
}

// GOOD
@Entity
class SomeEntity {
    private String name;
    
    public void updateName(String name) {
        this.name = name;
    }
}
```
- @Comment 주석으로 사용
- @Table 을 사용한다.
```java
// BAD
@Entity
class SomeEntity {
    private String name;
}

// GOOD
@Entity
@Table(name = "some_entity")
class SomeEntity {
    private String name;
}
```
- version 컬럼 디폴트 값 세팅 (벌크 insert 시 이슈 존재)
    - db 초기값 0 세팅
    - 엔터티 값 0 초기값 세팅
```java
// BAD
@Entity
@Table(name = "some_entity")
class SomeEntity {
    @Version
    private Long version;
}

// GOOD
@Entity
@Table(name = "some_entity")
class SomeEntity {
    @Version
    private Long version = 0L;
}
```

## DTO
### 외부에서 요청을 표현하는 클래스
- Controller, Consumer 에서 사용한다.
- Record class 를 사용한다.
```java
//BAD
class CreateReqDto {
    private String name;
    private int age;
}
//GOOD
public record CreateReqDto(String name, int age) {}
```
- 입력 데이터: ReqDto 를 postfix 로 사용한다
```java
//BAD
public record CreateRequest(String name, int age) {}
//GOOD
public record CreateReqDto(String name, int age) {}
```
- 출력 데이터: ResDto 를 postfix 로 사용한다.
```java
//BAD
public record CreateResponse(String name, int age) {}
//GOOD
public record CreateResDto(String name, int age) {}
```

### 서비스 계층에서 사용하는 클래스
- record 를 사용할 수 있다면 record 를 사용한다.
- 입력 데이터: Cmd 를 postfix 로 사용한다
```java
// BAD
public record CreateCommand (String name, int age) {}
// GOOD
public record CreateCmd (String name, int age) {}
```
- 출력 데이터: Result 를 postfix 로 사용한다.
```java
// BAD
public record CreateCompleteDto (String name, int age) {}
// GOOD
public record CreateResult (String name, int age) {}
```

## 계층별 모델 사용 제한과 매핑 전략
- controller
    - ReqDto -> Cmd, Result -> ResDto 로의 매핑을 담당한다.
    - entity 를 사용하지 않는다.
- service
    - entity를 사용한다.
    - cmd -> entity, entity -> result 로 매핑을 담당한다.
## 서비스 바운더리
- 비지니스 로직은 외부로 나가는 모듈(api, batch, consumer...)에서 작성한다.
- domain 모듈안에서는 repoService 만 작성한다.

## Common
- 상수의 경우는 최대한 하나의 공통 constant에서 관리한다.
- var 사용여부
    - production: 사용금지
    - 테스트 코드: 사용 가능
## Validation
- common.lang 을 활용하여 값 유효성 검증할 때 blank check 를 지향하자

### ValidationUtils 정책
- `validateNull`
    - `(final Object target, final String message, Object... args)`
        - message를 커스텀하게 사용하는 경우
    - `(final Object target, final String targetName)`
        - %s cannot be null 공통 메시지를 사용하는 경우
- `validateEmptyString`, `validateCollection` , `validateBlankString` 은 `validateNull` 과 동일하게 진행

- ValidationMessage 관련
    - domain/message 패키지 ValidationMessageConstants 파일 하나로 관리
        - 변수명 규칙: 도메인_벨리데이션규칙
            - ex) RMS_MOVE_STOCK_QUANTITY