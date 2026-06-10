import { useState, useEffect } from 'react';
import { API_BASE } from '../api';

interface Message {
  id: number;
  msg_id: string;
  article_id?: string;
  source: string;
  publish_time: string;
  content: string;
  title?: string;
  category?: string;
  is_important: boolean;
  has_image: boolean;
  reading_num: number;
  share_num: number;
  sentiment_label?: string;
  sentiment_score?: number;
  related_stocks?: string[];
}

interface MessageGroup {
  source: string;
  label: string;
  color: string;
  messages: Message[];
  loading: boolean;
}

const CATEGORY_MAP: Record<string, string> = {
  zc: '政策',
  gs: '公司',
  hy: '行业',
  sc: '市场',
};

const CATEGORY_COLORS: Record<string, string> = {
  zc: 'bg-red-100 text-red-800',
  gs: 'bg-blue-100 text-blue-800',
  hy: 'bg-green-100 text-green-800',
  sc: 'bg-purple-100 text-purple-800',
};

export default function Messages() {
  const [activeTab, setActiveTab] = useState('all');
  const [messageGroups, setMessageGroups] = useState<MessageGroup[]>([
    { source: 'telegram', label: '财联社电报', color: 'border-l-4 border-red-500', messages: [], loading: true },
    { source: 'a_share', label: 'A股消息', color: 'border-l-4 border-blue-500', messages: [], loading: true },
    { source: 'headline', label: '头条', color: 'border-l-4 border-orange-500', messages: [], loading: true },
    { source: 'global', label: '环球', color: 'border-l-4 border-green-500', messages: [], loading: true },
    { source: 'company_depth', label: '公司深度', color: 'border-l-4 border-purple-500', messages: [], loading: true },
  ]);
  const [filterCategory, setFilterCategory] = useState('');
  const [filterImportant, setFilterImportant] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchMessages = async (source: string, endpoint: string) => {
    try {
      const response = await fetch(`${API_BASE}${endpoint}?limit=20`);
      if (!response.ok) throw new Error('Failed to fetch');
      const data = await response.json();
      return data.map((msg: any) => ({
        ...msg,
        source,
        publish_time: msg.publish_time || msg.created_time || msg.ctime,
      }));
    } catch (error) {
      console.error(`Error fetching ${source}:`, error);
      return [];
    }
  };

  useEffect(() => {
    const loadAllMessages = async () => {
      const endpoints: Record<string, string> = {
        telegram: '/api/messagesrc/cls/telegram/list',
        a_share: '/api/messagesrc/cls/a-share/list',
        headline: '/api/messagesrc/cls/headline/list',
        global: '/api/messagesrc/cls/global/list',
        company_depth: '/api/messagesrc/cls/company-depth/list',
      };

      const updatedGroups = await Promise.all(
        messageGroups.map(async (group) => {
          const messages = await fetchMessages(group.source, endpoints[group.source]);
          return { ...group, messages, loading: false };
        })
      );

      setMessageGroups(updatedGroups);
    };

    loadAllMessages();
    const interval = setInterval(loadAllMessages, 30000);
    return () => clearInterval(interval);
  }, []);

  const getAllMessages = (): Message[] => {
    const all = messageGroups.flatMap(g => g.messages);
    return all.sort((a, b) => 
      new Date(b.publish_time).getTime() - new Date(a.publish_time).getTime()
    );
  };

  const filterMessages = (messages: Message[]): Message[] => {
    let filtered = messages;
    
    if (activeTab !== 'all') {
      const group = messageGroups.find(g => g.source === activeTab);
      filtered = group ? group.messages : [];
    }
    
    if (filterCategory) {
      filtered = filtered.filter(m => m.category === filterCategory);
    }
    
    if (filterImportant) {
      filtered = filtered.filter(m => m.is_important);
    }
    
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(m => 
        m.content.toLowerCase().includes(query) ||
        m.title?.toLowerCase().includes(query)
      );
    }
    
    return filtered;
  };

  const displayMessages = filterMessages(activeTab === 'all' ? getAllMessages() : []);

  const getSentimentBadge = (label?: string, score?: number) => {
    if (!label) return null;
    const colors: Record<string, string> = {
      positive: 'bg-green-100 text-green-800',
      negative: 'bg-red-100 text-red-800',
      neutral: 'bg-gray-100 text-gray-800',
    };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full ${colors[label] || colors.neutral}`}>
        {label === 'positive' ? '正面' : label === 'negative' ? '负面' : '中性'}
        {score !== undefined && ` ${(score * 100).toFixed(0)}%`}
      </span>
    );
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">消息中心</h1>
      
      {/* 筛选栏 */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-center">
          {/* 消息源标签 */}
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('all')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              全部
            </button>
            {messageGroups.map(group => (
              <button
                key={group.source}
                onClick={() => setActiveTab(group.source)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === group.source ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {group.label}
                {group.messages.length > 0 && (
                  <span className="ml-1 text-xs bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded-full">
                    {group.messages.length}
                  </span>
                )}
              </button>
            ))}
          </div>
          
          <div className="w-px h-6 bg-gray-300" />
          
          {/* 分类筛选 */}
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="px-3 py-1.5 border rounded-lg text-sm"
          >
            <option value="">全部分类</option>
            <option value="zc">政策</option>
            <option value="gs">公司</option>
            <option value="hy">行业</option>
            <option value="sc">市场</option>
          </select>
          
          {/* 重要标记 */}
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={filterImportant}
              onChange={(e) => setFilterImportant(e.target.checked)}
              className="rounded"
            />
            仅看重要
          </label>
          
          {/* 搜索 */}
          <div className="flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="搜索消息内容..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-3 py-1.5 border rounded-lg text-sm"
            />
          </div>
        </div>
      </div>

      {/* 消息列表 */}
      <div className="space-y-3">
        {messageGroups.some(g => g.loading) && displayMessages.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <div className="animate-spin inline-block w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mb-2" />
            <p>加载中...</p>
          </div>
        ) : displayMessages.length === 0 ? (
          <div className="text-center py-12 text-gray-500 bg-white rounded-lg shadow">
            <p>暂无消息</p>
          </div>
        ) : (
          displayMessages.map((msg, index) => (
            <div
              key={`${msg.source}-${msg.id}-${index}`}
              className={`bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow ${
                msg.is_important ? 'ring-2 ring-red-200' : ''
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  {/* 头部信息 */}
                  <div className="flex items-center gap-2 mb-2">
                    {msg.category && (
                      <span className={`text-xs px-2 py-0.5 rounded-full ${CATEGORY_COLORS[msg.category] || 'bg-gray-100'}`}>
                        {CATEGORY_MAP[msg.category] || msg.category}
                      </span>
                    )}
                    {msg.is_important && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-800 font-medium">
                        重要
                      </span>
                    )}
                    {getSentimentBadge(msg.sentiment_label, msg.sentiment_score)}
                    <span className="text-xs text-gray-400 ml-auto">
                      {new Date(msg.publish_time).toLocaleString('zh-CN')}
                    </span>
                  </div>
                  
                  {/* 标题 */}
                  {msg.title && (
                    <h3 className="font-medium text-gray-900 mb-1">{msg.title}</h3>
                  )}
                  
                  {/* 内容 */}
                  <p className="text-sm text-gray-700 leading-relaxed">{msg.content}</p>
                  
                  {/* 关联股票 */}
                  {msg.related_stocks && msg.related_stocks.length > 0 && (
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-xs text-gray-500">关联:</span>
                      {msg.related_stocks.map(stock => (
                        <span key={stock} className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded">
                          {stock}
                        </span>
                      ))}
                    </div>
                  )}
                  
                  {/* 底部信息 */}
                  <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
                    <span>阅读 {msg.reading_num || 0}</span>
                    <span>分享 {msg.share_num || 0}</span>
                    {msg.has_image && <span className="text-blue-500">📷 含图片</span>}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
