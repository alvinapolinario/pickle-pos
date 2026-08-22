class PosCustomer {
  const PosCustomer({
    required this.id,
    required this.name,
    this.mobile = '',
    this.email = '',
    this.membershipTier = '',
    this.canteenDiscountPct = '0',
    this.courtDiscountPct = '0',
    this.loyaltyPoints = 0,
  });

  factory PosCustomer.fromJson(Map<String, dynamic> json) {
    return PosCustomer(
      id: json['id'] as int,
      name: '${json['name']}',
      mobile: '${json['mobile'] ?? ''}',
      email: '${json['email'] ?? ''}',
      membershipTier: '${json['membership_tier'] ?? ''}',
      canteenDiscountPct: '${json['canteen_discount_pct'] ?? '0'}',
      courtDiscountPct: '${json['court_discount_pct'] ?? '0'}',
      loyaltyPoints: (json['loyalty_points'] as num?)?.toInt() ?? 0,
    );
  }

  final int id;
  final String name;
  final String mobile;
  final String email;
  final String membershipTier;
  final String canteenDiscountPct;
  final String courtDiscountPct;
  final int loyaltyPoints;

  bool get isMember => membershipTier.isNotEmpty;

  String get subtitle {
    final bits = <String>[
      if (mobile.isNotEmpty) mobile,
      if (isMember) membershipTier,
      if (loyaltyPoints > 0) '$loyaltyPoints pts',
    ];
    return bits.isEmpty ? 'Saved profile' : bits.join(' · ');
  }

  String get canteenLabel {
    if (!_hasDiscount(canteenDiscountPct)) return isMember ? membershipTier : 'Member';
    return '$membershipTier · $canteenDiscountPct% canteen';
  }

  String get courtLabel {
    if (!_hasDiscount(courtDiscountPct)) return isMember ? membershipTier : 'Member';
    return '$membershipTier · $courtDiscountPct% court';
  }

  bool _hasDiscount(String value) {
    final amount = double.tryParse(value) ?? 0;
    return amount > 0;
  }
}
