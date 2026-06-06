import 'package:flutter/material.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/services.dart';
import 'screens/app_shell.dart';
import 'theme/app_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // 允許直式與橫式
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
    DeviceOrientation.landscapeLeft,
    DeviceOrientation.landscapeRight,
  ]);
  runApp(const SavestockApp());
}

class SavestockApp extends StatelessWidget {
  const SavestockApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '存股追蹤',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.theme,
      // 讓桌機 / web 的滑鼠拖曳也能捲動，否則 RefreshIndicator 無法下拉
      scrollBehavior: _AppScrollBehavior(),
      home: const AppShell(),
    );
  }
}

/// 預設的 MaterialScrollBehavior 在 web/桌機不含 mouse 拖曳，
/// 補上 mouse 讓清單可用滑鼠下拉觸發 RefreshIndicator。
class _AppScrollBehavior extends MaterialScrollBehavior {
  @override
  Set<PointerDeviceKind> get dragDevices => {
        PointerDeviceKind.touch,
        PointerDeviceKind.mouse,
        PointerDeviceKind.trackpad,
        PointerDeviceKind.stylus,
      };
}
