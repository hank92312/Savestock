import 'package:flutter/material.dart';
import 'package:web/web.dart' as web;
import '../theme/app_theme.dart';

/// 頂部全域模組切換列：存股追蹤（本 App）｜ ETF 追蹤（Django 網頁）。
///
/// 與 ETF 網站 base.html 的分段切換列樣式一致，達成兩模組跨站一鍵互跳。
/// 「存股追蹤」為目前所在（active），點「ETF 追蹤」直接切換到 ETF 網站。
class ModuleSwitchBar extends StatelessWidget {
  const ModuleSwitchBar({super.key});

  /// ETF 追蹤網站網址（Django on Cloud Run）。
  /// 本地開發時如需互跳測試，改成 'http://127.0.0.1:8010/etf' 即可指向本機伺服器。
  static const String etfSiteUrl =
      'https://savestock-report-62102931839.asia-east1.run.app/etf';

  void _openEtf() => web.window.open(etfSiteUrl, '_self');

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      child: Container(
        decoration: const BoxDecoration(
          border: Border(bottom: BorderSide(color: AppTheme.divider)),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Row(
          children: [
            const Text(
              'Savestock',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w800,
                color: AppTheme.textPrimary,
              ),
            ),
            const SizedBox(width: 12),
            // 分段切換控制
            Container(
              padding: const EdgeInsets.all(3),
              decoration: BoxDecoration(
                color: AppTheme.surface,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _segment(label: '存股追蹤', active: true, onTap: null),
                  _segment(label: 'ETF 追蹤', active: false, onTap: _openEtf),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _segment({
    required String label,
    required bool active,
    VoidCallback? onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
        decoration: BoxDecoration(
          color: active ? Colors.white : Colors.transparent,
          borderRadius: BorderRadius.circular(9),
          boxShadow: active
              ? const [
                  BoxShadow(
                    color: Color(0x1F202C44),
                    blurRadius: 4,
                    offset: Offset(0, 1),
                  ),
                ]
              : null,
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w700,
            color: active ? AppTheme.primary : AppTheme.textSecondary,
          ),
        ),
      ),
    );
  }
}
