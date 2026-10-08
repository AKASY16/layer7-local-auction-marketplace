package com.layer7.marketplace.region.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "regions")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Region {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@Column(name = "region_code", nullable = false, unique = true, length = 20)
	private String regionCode;

	@Column(name = "sido_name", nullable = false, length = 50)
	private String sidoName;

	@Column(name = "sigungu_name", nullable = false, length = 50)
	private String sigunguName;
}
