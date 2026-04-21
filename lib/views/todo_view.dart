import 'package:flutter/material.dart';
import 'package:flutter_slidable/flutter_slidable.dart';

class TodoView extends StatefulWidget {
  const TodoView({super.key});

  @override
  State<TodoView> createState() => _TodoViewState();
}

class _TodoViewState extends State<TodoView> {
  List<TodoItem> _todos = [
    TodoItem('完成项目文档', false),
    TodoItem('准备会议资料', false),
    TodoItem('锻炼身体', true),
  ];

  final TextEditingController _controller = TextEditingController();

  void _addTodo() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('添加待办'),
        content: TextField(
          controller: _controller,
          decoration: const InputDecoration(hintText: '输入待办事项'),
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
                  _todos.add(TodoItem(_controller.text, false));
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

  void _toggleTodo(int index) {
    setState(() {
      _todos[index].isCompleted = !_todos[index].isCompleted;
    });
  }

  void _deleteTodo(int index) {
    setState(() {
      _todos.removeAt(index);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: ListView.builder(
        itemCount: _todos.length,
        itemBuilder: (context, index) {
          final todo = _todos[index];
          return Slidable(
            endActionPane: ActionPane(
              motion: const ScrollMotion(),
              children: [
                SlidableAction(
                  onPressed: (_) => _deleteTodo(index),
                  backgroundColor: const Color(0xFFFE4A49),
                  foregroundColor: Colors.white,
                  icon: Icons.delete,
                  label: '删除',
                ),
              ],
            ),
            child: CheckboxListTile(
              title: Text(
                todo.title,
                style: TextStyle(
                  decoration: todo.isCompleted ? TextDecoration.lineThrough : null,
                  color: todo.isCompleted ? Colors.grey : Colors.black,
                ),
              ),
              value: todo.isCompleted,
              onChanged: (_) => _toggleTodo(index),
              activeColor: const Color(0xFF007AFF),
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _addTodo,
        child: const Icon(Icons.add),
      ),
    );
  }
}

class TodoItem {
  String title;
  bool isCompleted;

  TodoItem(this.title, this.isCompleted);
}