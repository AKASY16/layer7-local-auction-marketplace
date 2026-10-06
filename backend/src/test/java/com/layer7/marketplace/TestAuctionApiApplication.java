package com.layer7.marketplace;

import org.springframework.boot.SpringApplication;

public class TestAuctionApiApplication {

	public static void main(String[] args) {
		SpringApplication.from(AuctionApiApplication::main).with(TestcontainersConfiguration.class).run(args);
	}

}
