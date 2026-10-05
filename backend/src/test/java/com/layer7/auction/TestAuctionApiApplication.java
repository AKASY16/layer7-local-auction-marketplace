package com.layer7.auction;

import org.springframework.boot.SpringApplication;

public class TestAuctionApiApplication {

	public static void main(String[] args) {
		SpringApplication.from(AuctionApiApplication::main).with(TestcontainersConfiguration.class).run(args);
	}

}
