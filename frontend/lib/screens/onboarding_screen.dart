import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/app_theme.dart';

/// App 內教學導覽：首次開啟自動顯示，亦可從首頁 ❓ 入口隨時再看。
class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  static const _seenKey = 'onboarding_seen';

  /// 是否已看過導覽（首次啟動判斷用）
  static Future<bool> hasSeen() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_seenKey) ?? false;
  }

  static Future<void> _markSeen() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_seenKey, true);
  }

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _controller = PageController();
  int _page = 0;

  static const _pages = <_OnboardPage>[
    _OnboardPage(
      icon: Icons.savings_rounded,
      color: AppTheme.gainGreen,
      title: '什麼是存股與殖利率',
      body: '存股＝長期持有會穩定配息的好公司，靠每年股利累積被動收入。\n\n'
          '殖利率 = 年現金股利 ÷ 股價 × 100%。\n'
          '配息相同時，股價越低、殖利率越高。',
    ),
    _OnboardPage(
      icon: Icons.bar_chart_rounded,
      color: AppTheme.primary,
      title: '怎麼使用這個 App',
      body: '「預設清單」精選存股標的，依估算殖利率高低排序。\n\n'
          '點任一檔看詳情：殖利率大字、近年平均股利、價格走勢圖。\n\n'
          '喜歡的股票可加入「我的股票」持續追蹤。',
    ),
    _OnboardPage(
      icon: Icons.search_rounded,
      color: Color(0xFF7E57C2),
      title: '搜尋你關注的股票',
      body: '點首頁右上角的 🔍 搜尋，輸入代號或名稱，'
          '即可查詢全台上市股票與 ETF。\n\n'
          '查到後一鍵加入「我的股票」，建立專屬追蹤清單。\n\n'
          '「我的股票」每次開啟都會自動更新最新股價與殖利率。',
    ),
    _OnboardPage(
      icon: Icons.warning_rounded,
      color: AppTheme.alertRed,
      title: '警示：避開高殖利率陷阱',
      body: '高殖利率有時是「股價暴跌」造成的假象。\n\n'
          '本 App 會在單日暴跌或成交爆量時，標記紅色警示提醒你留意，'
          '而不是盲目追高息。',
    ),
    _OnboardPage(
      icon: Icons.info_outline_rounded,
      color: AppTheme.textSecondary,
      title: '重要：投資風險提醒',
      body: '本 App 提供的數據與殖利率僅供參考，'
          '不構成任何投資建議。\n\n'
          '股市有風險，投資前請自行評估，並為自己的決策負責。',
    ),
  ];

  bool get _isLast => _page == _pages.length - 1;

  Future<void> _finish() async {
    await OnboardingScreen._markSeen();
    if (mounted) Navigator.of(context).pop();
  }

  void _next() {
    if (_isLast) {
      _finish();
    } else {
      _controller.nextPage(
        duration: const Duration(milliseconds: 280),
        curve: Curves.easeInOut,
      );
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Column(
          children: [
            // 略過
            Align(
              alignment: Alignment.centerRight,
              child: Padding(
                padding: const EdgeInsets.only(right: 8, top: 4),
                child: _isLast
                    ? const SizedBox(height: 48)
                    : TextButton(
                        onPressed: _finish,
                        child: const Text('略過',
                            style: TextStyle(color: AppTheme.textSecondary)),
                      ),
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: _controller,
                itemCount: _pages.length,
                onPageChanged: (i) => setState(() => _page = i),
                itemBuilder: (_, i) => _pages[i],
              ),
            ),
            // 頁碼點
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(_pages.length, (i) {
                final active = i == _page;
                return AnimatedContainer(
                  duration: const Duration(milliseconds: 250),
                  margin: const EdgeInsets.symmetric(horizontal: 4),
                  width: active ? 22 : 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: active ? AppTheme.primary : AppTheme.divider,
                    borderRadius: BorderRadius.circular(4),
                  ),
                );
              }),
            ),
            const SizedBox(height: 24),
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 0, 24, 28),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _next,
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                  ),
                  child: Text(_isLast ? '開始使用' : '下一頁',
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w700)),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── 單頁內容 ──────────────────────────────────────────────────

class _OnboardPage extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String title;
  final String body;

  const _OnboardPage({
    required this.icon,
    required this.color,
    required this.title,
    required this.body,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 104,
            height: 104,
            decoration: BoxDecoration(
              color: color.withOpacity(0.10),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, size: 52, color: color),
          ),
          const SizedBox(height: 32),
          Text(
            title,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w800,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            body,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 15,
              height: 1.6,
              color: AppTheme.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}
