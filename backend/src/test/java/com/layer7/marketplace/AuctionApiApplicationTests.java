package com.layer7.marketplace;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;

@Import(TestcontainersConfiguration.class)
@SpringBootTest
class AuctionApiApplicationTests {

	@Test
	void contextLoads() {
	}

}
