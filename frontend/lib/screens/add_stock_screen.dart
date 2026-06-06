import 'dart:async';
import 'package:flutter/material.dart';
import '../models/stock.dart';
import '../services/api_service.dart';
import '../services/user_service.dart';
import '../theme/app_theme.dart';
import '../widgets/stock_card.dart';

class AddStockScreen extends StatefulWidget {
  const AddStockScreen({super.key});

  @override
  State<AddStockScreen> createState() => _AddStockScreenState();
}

class _AddStockScreenState extends State<AddStockScreen> {
  final _controller = TextEditingController();
  Timer? _debounce;

  // 候選清單狀態
  List<SearchCandidate> _candidates = [];
  bool _loadingCandidates = false;
  String? _noResultsQuery; // 搜尋回傳空清單時記錄查詢詞，供「直接查詢」使用

  // 選取後查詢結果狀態
  Stock? _result;
  bool _searching = false;
  bool _adding = false;
  String? _error;
  bool _added = false;

  @override
  void initState() {
    super.initState();
    _controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.removeListener(_onTextChanged);
    _controller.dispose();
    super.dispose();
  }

  void _onTextChanged() {
    final q = _controller.text.trim();

    // 清空已選結果
    if (_result != null || _error != null || _noResultsQuery != null) {
      setState(() {
        _result = null;
        _error = null;
        _added = false;
        _noResultsQuery = null;
      });
    }

    // 清空輸入時隱藏候選
    if (q.isEmpty) {
      _debounce?.cancel();
      setState(() => _candidates = []);
      return;
    }

    // Debounce 300ms
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () => _searchCandidates(q));
  }

  Future<void> _searchCandidates(String q) async {
    setState(() => _loadingCandidates = true);
    try {
      final candidates = await ApiService.searchStocks(q);
      if (!mounted) return;
      setState(() {
        _candidates = candidates;
        _noResultsQuery = candidates.isEmpty ? q : null;
        _loadingCandidates = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() { _loadingCandidates = false; _noResultsQuery = null; });
    }
  }

  Future<void> _selectCandidate(SearchCandidate candidate) async {
    setState(() {
      _candidates = [];
      _searching = true;
      _result = null;
      _error = null;
      _added = false;
      _controller.text = candidate.code; // 填入純代號
    });

    try {
      final stock = await ApiService.lookupStock(candidate.stockId);
      if (!mounted) return;
      setState(() {
        _result = stock;
        _searching = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _searching = false;
      });
    }
  }

  Future<void> _directLookup(String code) async {
    setState(() => _noResultsQuery = null);
    await _selectCandidate(SearchCandidate(stockId: code, name: code));
  }

  Future<void> _add() async {
    if (_result == null) return;
    setState(() => _adding = true);

    try {
      final userId = await UserService.getOrCreateUserId();
      final error = await ApiService.addToWatchlist(userId, _result!.stockId);

      if (!mounted) return;
      if (error != null) {
        setState(() {
          _error = error;
          _adding = false;
        });
        return;
      }
      setState(() {
        _added = true;
        _adding = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = '加入失敗，請確認網路連線後再試';
        _adding = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final isTablet = width >= 600;

    return Scaffold(
      appBar: AppBar(title: const Text('查詢股票')),
      body: Column(
        children: [
          _SearchBar(
            controller: _controller,
            isSearching: _searching || _loadingCandidates,
          ),
          const Divider(height: 1, color: AppTheme.divider),
          Expanded(
            child: _searching
                ? const _LoadingView()
                : _result != null
                    ? _ResultView(
                        stock: _result!,
                        isTablet: isTablet,
                        added: _added,
                        adding: _adding,
                        error: _error,
                        onAdd: _added ? null : _add,
                      )
                    : _candidates.isNotEmpty
                        ? _CandidateList(
                            candidates: _candidates,
                            onSelect: _selectCandidate,
                          )
                        : _noResultsQuery != null && _error == null
                            ? _NoResultsView(
                                query: _noResultsQuery!,
                                onDirectLookup: _directLookup,
                              )
                            : _EmptyView(
                                error: _error,
                                showLoading: _loadingCandidates,
                              ),
          ),
        ],
      ),
    );
  }
}

// ── 搜尋列 ──────────────────────────────────────────────────────

class _SearchBar extends StatelessWidget {
  final TextEditingController controller;
  final bool isSearching;

  const _SearchBar({required this.controller, required this.isSearching});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: TextField(
        controller: controller,
        autofocus: true,
        keyboardType: TextInputType.text,
        textInputAction: TextInputAction.search,
        decoration: InputDecoration(
          hintText: '輸入股票代號或中文名稱（如 0050、台積電）',
          prefixIcon: const Icon(Icons.search_rounded),
          suffixIcon: isSearching
              ? const Padding(
                  padding: EdgeInsets.all(14),
                  child: SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                )
              : null,
          filled: true,
          fillColor: AppTheme.surface,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: AppTheme.divider),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: AppTheme.divider),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: AppTheme.primary, width: 2),
          ),
          contentPadding:
              const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
        ),
      ),
    );
  }
}

// ── 候選清單 ────────────────────────────────────────────────────

class _CandidateList extends StatelessWidget {
  final List<SearchCandidate> candidates;
  final ValueChanged<SearchCandidate> onSelect;

  const _CandidateList({required this.candidates, required this.onSelect});

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      itemCount: candidates.length,
      separatorBuilder: (_, __) =>
          const Divider(height: 1, indent: 56, color: AppTheme.divider),
      itemBuilder: (context, i) {
        final c = candidates[i];
        return ListTile(
          leading: Container(
            width: 40,
            height: 40,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: AppTheme.primary.withOpacity(0.08),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              c.code.length <= 4 ? c.code : c.code.substring(0, 4),
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: AppTheme.primary,
              ),
            ),
          ),
          title: Text(
            c.name,
            style: const TextStyle(
              fontWeight: FontWeight.w600,
              fontSize: 15,
            ),
          ),
          subtitle: Text(
            c.code,
            style: const TextStyle(
              color: AppTheme.textSecondary,
              fontSize: 13,
            ),
          ),
          trailing: const Icon(
            Icons.chevron_right_rounded,
            color: AppTheme.textSecondary,
          ),
          onTap: () => onSelect(c),
        );
      },
    );
  }
}

// ── 查詢結果 ──────────────────────────────────────────────────

class _ResultView extends StatelessWidget {
  final Stock stock;
  final bool isTablet;
  final bool added;
  final bool adding;
  final String? error;
  final VoidCallback? onAdd;

  const _ResultView({
    required this.stock,
    required this.isTablet,
    required this.added,
    required this.adding,
    this.error,
    this.onAdd,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '查詢結果',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: AppTheme.textSecondary,
            ),
          ),
          const SizedBox(height: 12),
          StockCard(stock: stock, isTablet: isTablet),
          const SizedBox(height: 16),
          if (error != null) _Banner(message: error!, isError: true),
          if (added)
            const _Banner(
              message: '已加入我的股票，下次開啟時將自動更新最新資料',
              isError: false,
            ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: added
                ? OutlinedButton.icon(
                    onPressed: () => Navigator.pop(context, true),
                    icon: const Icon(Icons.check_rounded),
                    label: const Text('返回我的股票'),
                  )
                : FilledButton.icon(
                    onPressed: adding ? null : onAdd,
                    icon: adding
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white),
                          )
                        : const Icon(Icons.bookmark_add_rounded),
                    label: Text(adding ? '加入中…' : '加入我的股票'),
                    style: FilledButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

// ── 找不到候選結果 ─────────────────────────────────────────────

class _NoResultsView extends StatelessWidget {
  final String query;
  final ValueChanged<String> onDirectLookup;
  const _NoResultsView({required this.query, required this.onDirectLookup});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.search_off_rounded,
                size: 56, color: AppTheme.textSecondary),
            const SizedBox(height: 16),
            Text(
              '找不到「$query」相關股票',
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: AppTheme.textPrimary,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              '若確定代號正確，可直接查詢（部分股票不在搜尋索引中）',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13, color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: () => onDirectLookup(query),
              icon: const Icon(Icons.search_rounded, size: 18),
              label: Text('直接查詢「$query」'),
              style: FilledButton.styleFrom(
                padding:
                    const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── 初始 / 錯誤畫面 ──────────────────────────────────────────

class _EmptyView extends StatelessWidget {
  final String? error;
  final bool showLoading;
  const _EmptyView({this.error, this.showLoading = false});

  @override
  Widget build(BuildContext context) {
    if (showLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(40),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.search_off_rounded,
                  size: 56, color: AppTheme.textSecondary),
              const SizedBox(height: 16),
              Text(
                error!,
                textAlign: TextAlign.center,
                style: const TextStyle(
                    color: AppTheme.textSecondary, fontSize: 15),
              ),
            ],
          ),
        ),
      );
    }

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.manage_search_rounded,
                size: 64, color: Colors.grey.shade300),
            const SizedBox(height: 20),
            const Text(
              '搜尋任意台股',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: AppTheme.textPrimary,
              ),
            ),
            const SizedBox(height: 10),
            const Text(
              '輸入代號或中文名稱（部分亦可）\n系統會即時列出匹配股票供你選擇\n\n例如：\n「005」→ 0050、0051、0056…\n「台積」→ 台積電(2330)\n「金融」→ 國泰金、富邦金…',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14,
                color: AppTheme.textSecondary,
                height: 1.7,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── 載入中 ─────────────────────────────────────────────────────

class _LoadingView extends StatelessWidget {
  const _LoadingView();

  @override
  Widget build(BuildContext context) => const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('從網路查詢股票資料中…',
                style: TextStyle(color: AppTheme.textSecondary)),
          ],
        ),
      );
}

// ── 訊息橫幅 ──────────────────────────────────────────────────

class _Banner extends StatelessWidget {
  final String message;
  final bool isError;
  const _Banner({required this.message, required this.isError});

  @override
  Widget build(BuildContext context) {
    final color = isError ? AppTheme.alertRed : AppTheme.gainGreen;
    final icon = isError ? Icons.info_outline : Icons.check_circle_outline;
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                  color: color, fontSize: 13, fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}
