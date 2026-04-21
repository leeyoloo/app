import 'package:flutter/material.dart';
import 'package:flutter_slidable/flutter_slidable.dart';

class MemosView extends StatefulWidget {
  const MemosView({super.key});

  @override
  State<MemosView> createState() => _MemosViewState();
}

class _MemosViewState extends State<MemosView> {
  List<MemoItem> _memos = [
    MemoItem('买牛奶', Colors.yellow[100]!),
    MemoItem('取快递', Colors.blue[100]!),
    MemoItem('整理房间', Colors.green[100]!),
  ];

  final TextEditingController _controller = TextEditingController();
  Color _selectedColor = Colors.yellow[100]!;

  final List<Color> _colors = [
    Colors.yellow[100]!,
    Colors.blue[100]!,
    Colors.green[100]!,
    Colors.red[100]!,
    Colors.purple[100]!,
    Colors.orange[100]!,
  ];

  void _addMemo() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('添加便签'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _controller,
              decoration: const InputDecoration(hintText: '输入便签内容'),
              maxLines: 3,
            ),
            const SizedBox(height: 16),
            const Text('选择颜色'),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: _colors.map((color) {
                return GestureDetector(
                  onTap: () {
                    setState(() {
                      _selectedColor = color;
                    });
                  },
                  child: Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: color,
                      borderRadius: BorderRadius.circular(8),
                      border: _selectedColor == color
                          ? Border.all(color: Colors.black, width: 2)
                          : null,
                    ),
                  ),
                );
              }).toList(),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              if (_controller.text.isNotEmpty) {
                setState(() {
                  _memos.add(MemoItem(_controller.text, _selectedColor));
                });
                _controller.clear();
                Navigator.pop(context);
              }
            },
            child: const Text('添加'),
          ),
        ],
      ),
    );
  }

  void _deleteMemo(int index) {
    setState(() {
      _memos.removeAt(index);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: GridView.builder(
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            crossAxisSpacing: 16,
            mainAxisSpacing: 16,
          ),
          itemCount: _memos.length,
          itemBuilder: (context, index) {
            final memo = _memos[index];
            return Slidable(
              endActionPane: ActionPane(
                motion: const ScrollMotion(),
                children: [
                  SlidableAction(
                    onPressed: (_) => _deleteMemo(index),
                    backgroundColor: const Color(0xFFFE4A49),
                    foregroundColor: Colors.white,
                    icon: Icons.delete,
                    label: '删除',
                  ),
                ],
              ),
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: memo.color,
                  borderRadius: BorderRadius.circular(8),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.grey.withOpacity(0.2),
                      spreadRadius: 2,
                      blurRadius: 4,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Text(
                  memo.content,
                  style: const TextStyle(fontSize: 14),
                ),
              ),
            );
          },
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _addMemo,
        child: const Icon(Icons.add),
      ),
    );
  }
}

class MemoItem {
  String content;
  Color color;

  MemoItem(this.content, this.color);
}