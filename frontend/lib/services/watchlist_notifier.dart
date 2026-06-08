import 'package:flutter/foundation.dart';

class WatchlistNotifier extends ChangeNotifier {
  static final WatchlistNotifier instance = WatchlistNotifier._();
  WatchlistNotifier._();

  void markDirty() => notifyListeners();
}
